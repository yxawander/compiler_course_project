from __future__ import annotations

from dataclasses import dataclass

from nfa.nfa_node import NFANode


@dataclass(frozen=True)
class NFA:
    """NFA 结构：起始结点与结束结点。"""

    start_node: NFANode
    end_node: NFANode

    def __str__(self) -> str:
        return f"NFA(Start:{self.start_node.state_id}, End:{self.end_node.state_id})"
