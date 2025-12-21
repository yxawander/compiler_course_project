from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set

from dfa.dfa_state import DFAState


@dataclass
class DFA:
    start_state: DFAState
    states: List[DFAState]
    alphabet: Set[str]

    def get_state_by_id(self, state_id: int) -> Optional[DFAState]:
        for state in self.states:
            if state.state_id == state_id:
                return state
        return None

    def __str__(self) -> str:
        lines: List[str] = []
        lines.append("DFA:")
        lines.append(f"起始状态: {self.start_state.state_id}")
        accepting = [str(s.state_id) for s in self.states if s.is_accepting]
        lines.append("接受状态: " + " ".join(accepting))
        lines.append(f"字母表: {sorted(self.alphabet)}")
        lines.append("转移表:")
        for state in self.states:
            for symbol in sorted(self.alphabet):
                target = state.get_transition(symbol)
                if target is not None:
                    lines.append(f"  {state.state_id} --{symbol}--> {target.state_id}")
        return "\n".join(lines)
