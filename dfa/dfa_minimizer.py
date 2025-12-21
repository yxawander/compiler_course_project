from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Set

from .dfa import DFA
from .dfa_state import DFAState


@dataclass
class DFAMinimizer:
    def minimize(self, original_dfa: DFA) -> DFA:
        partition = self._create_initial_partition(original_dfa)
        partition = self._hopcroft_minimization(original_dfa, partition)
        return self._build_minimized_dfa(original_dfa, partition)

    @staticmethod
    def _create_initial_partition(dfa: DFA) -> List[Set[DFAState]]:
        accepting: Set[DFAState] = set()
        non_accepting: Set[DFAState] = set()

        for state in dfa.states:
            if state.is_accepting:
                accepting.add(state)
            else:
                non_accepting.add(state)

        parts: List[Set[DFAState]] = []
        if accepting:
            parts.append(accepting)
        if non_accepting:
            parts.append(non_accepting)
        return parts

    def _hopcroft_minimization(self, dfa: DFA, initial_partition: List[Set[DFAState]]) -> List[Set[DFAState]]:
        work_set: Deque[Set[DFAState]] = deque(initial_partition)
        partition: List[Set[DFAState]] = list(initial_partition)

        while work_set:
            A = work_set.popleft()

            for symbol in dfa.alphabet:
                X = self._find_predecessors(dfa, A, symbol)
                if not X:
                    continue

                new_partition: List[Set[DFAState]] = []
                changed = False

                for Y in partition:
                    Y1: Set[DFAState] = set()
                    Y2: Set[DFAState] = set()

                    for state in Y:
                        (Y1 if state in X else Y2).add(state)

                    if Y1 and Y2:
                        new_partition.append(Y1)
                        new_partition.append(Y2)
                        changed = True

                        # Python 的 set 无法直接判断“contains Y”是否同一对象，
                        # 这里用集合相等判断来复刻 Java workSet.contains(Y)
                        idx_to_remove = None
                        for idx, item in enumerate(work_set):
                            if item == Y:
                                idx_to_remove = idx
                                break
                        if idx_to_remove is not None:
                            # 移除该元素
                            work_set.rotate(-idx_to_remove)
                            work_set.popleft()
                            work_set.rotate(idx_to_remove)
                            work_set.append(Y1)
                            work_set.append(Y2)
                        else:
                            work_set.append(Y1 if len(Y1) <= len(Y2) else Y2)
                    else:
                        new_partition.append(Y)

                if changed:
                    partition = new_partition

        return partition

    @staticmethod
    def _find_predecessors(dfa: DFA, target_set: Set[DFAState], symbol: str) -> Set[DFAState]:
        predecessors: Set[DFAState] = set()
        for state in dfa.states:
            nxt = state.get_transition(symbol)
            if nxt is not None and nxt in target_set:
                predecessors.add(state)
        return predecessors

    @staticmethod
    def _get_nfa_states_union(states: Set[DFAState]) -> Set[int]:
        union: Set[int] = set()
        for state in states:
            union |= set(state.nfa_states)
        return union

    def _build_minimized_dfa(self, original_dfa: DFA, final_partition: List[Set[DFAState]]) -> DFA:
        state_mapping: Dict[DFAState, DFAState] = {}
        new_states: List[DFAState] = []
        block_to_state: Dict[frozenset[DFAState], DFAState] = {}

        new_state_id = 0
        for block in final_partition:
            new_state = DFAState(new_state_id, self._get_nfa_states_union(block))
            new_state_id += 1
            new_state.is_accepting = any(s.is_accepting for s in block)

            new_states.append(new_state)
            block_to_state[frozenset(block)] = new_state

            for old_state in block:
                state_mapping[old_state] = new_state

        # 建转移：选 block 内任一代表状态即可
        for block in final_partition:
            rep = next(iter(block))
            new_state = block_to_state[frozenset(block)]

            for symbol in original_dfa.alphabet:
                old_target = rep.get_transition(symbol)
                if old_target is None:
                    continue
                new_target = state_mapping.get(old_target)
                if new_target is not None:
                    new_state.add_transition(symbol, new_target)

        new_start_state = state_mapping[original_dfa.start_state]
        return DFA(start_state=new_start_state, states=new_states, alphabet=set(original_dfa.alphabet))
