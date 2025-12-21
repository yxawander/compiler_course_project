from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, FrozenSet, List, Optional, Set

from nfa.nfa import NFA
from nfa.nfa_node import NFANode
from dfa.dfa import DFA
from dfa.dfa_state import DFAState


@dataclass
class NFAToDFAConverter:
    nfa: NFA

    def __post_init__(self) -> None:
        self._alphabet: Set[str] = self._extract_alphabet(self.nfa)
        self._dfa_state_counter: int = 0

    @staticmethod
    def _extract_alphabet(nfa: NFA) -> Set[str]:
        symbols: Set[str] = set()
        visited: Set[int] = set()
        stack: Deque[NFANode] = deque([nfa.start_node])

        while stack:
            current = stack.pop()
            if current.state_id in visited:
                continue
            visited.add(current.state_id)

            if current.path_char is not None:
                symbols.add(current.path_char)

            for nxt in current.next_nodes:
                if nxt.state_id not in visited:
                    stack.append(nxt)

        return symbols

    def _find_nfa_node_by_id(self, state_id: int) -> Optional[NFANode]:
        visited: Set[int] = set()
        stack: Deque[NFANode] = deque([self.nfa.start_node])

        while stack:
            current = stack.pop()
            if current.state_id in visited:
                continue
            visited.add(current.state_id)

            if current.state_id == state_id:
                return current

            for nxt in current.next_nodes:
                if nxt.state_id not in visited:
                    stack.append(nxt)

        return None

    def _epsilon_closure(self, states: Set[int]) -> Set[int]:
        closure: Set[int] = set(states)
        stack: Deque[int] = deque(states)

        while stack:
            state_id = stack.pop()
            node = self._find_nfa_node_by_id(state_id)
            if node is None:
                continue

            # 仅当 node.path_char 为 None 时，next_nodes 才当 ε 边
            if node.path_char is None:
                for nxt in node.next_nodes:
                    if nxt.state_id not in closure:
                        closure.add(nxt.state_id)
                        stack.append(nxt.state_id)

        return closure

    def _move(self, states: Set[int], symbol: str) -> Set[int]:
        result: Set[int] = set()
        for state_id in states:
            node = self._find_nfa_node_by_id(state_id)
            if node is None:
                continue

            if node.path_char is not None and node.path_char == symbol:
                for nxt in node.next_nodes:
                    result.add(nxt.state_id)

        return result

    def _contains_accepting_state(self, states: Set[int]) -> bool:
        return self.nfa.end_node.state_id in states

    def convert_to_dfa(self) -> DFA:
        dfa_states: List[DFAState] = []
        state_map: Dict[FrozenSet[int], DFAState] = {}
        unprocessed: Deque[DFAState] = deque()

        start_nfa_states = {self.nfa.start_node.state_id}
        start_closure = self._epsilon_closure(start_nfa_states)
        start_key = frozenset(start_closure)

        start_state = DFAState(self._dfa_state_counter, set(start_closure))
        self._dfa_state_counter += 1
        start_state.is_accepting = self._contains_accepting_state(start_closure)

        dfa_states.append(start_state)
        state_map[start_key] = start_state
        unprocessed.append(start_state)

        while unprocessed:
            current = unprocessed.pop()

            for symbol in self._alphabet:
                moved = self._move(current.nfa_states, symbol)
                if not moved:
                    continue

                new_closure = self._epsilon_closure(moved)
                key = frozenset(new_closure)
                new_state = state_map.get(key)

                if new_state is None:
                    new_state = DFAState(self._dfa_state_counter, set(new_closure))
                    self._dfa_state_counter += 1
                    new_state.is_accepting = self._contains_accepting_state(new_closure)
                    dfa_states.append(new_state)
                    state_map[key] = new_state
                    unprocessed.append(new_state)

                current.add_transition(symbol, new_state)

        return DFA(start_state=start_state, states=dfa_states, alphabet=set(self._alphabet))
