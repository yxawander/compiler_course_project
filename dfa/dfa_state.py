from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set


@dataclass(eq=False)
class DFAState:
    state_id: int
    nfa_states: Set[int]
    transitions: Dict[str, "DFAState"] = field(default_factory=dict)
    is_accepting: bool = False

    def add_transition(self, symbol: str, target_state: "DFAState") -> None:
        if len(symbol) != 1:
            raise ValueError("symbol must be a single character")
        self.transitions[symbol] = target_state

    def get_transition(self, symbol: str) -> Optional["DFAState"]:
        return self.transitions.get(symbol)

    def get_transition_symbols(self) -> Set[str]:
        return set(self.transitions.keys())

    def __str__(self) -> str:
        accept = "[ACCEPT]" if self.is_accepting else ""
        return f"DFAState{self.state_id}{sorted(self.nfa_states)}{accept}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DFAState):
            return False
        return self.nfa_states == other.nfa_states

    def __hash__(self) -> int:
        return hash(frozenset(self.nfa_states))
