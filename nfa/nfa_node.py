from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass(eq=False)
class NFANode:
    """NFA 结点。

    - path_char 为 None 表示 ε 转移结点
    - add_transition 会设置 path_char，并把 target 加入 next_nodes
    - add_epsilon_transition 只加入 next_nodes

    注意：该设计假定一个结点要么是字符转移（path_char != None），要么是 ε 结点（path_char == None）。
    """

    state_id: int
    path_char: Optional[str] = None
    next_nodes: List[NFANode] = field(default_factory=list)

    def add_transition(self, character: str, target_node: NFANode) -> None:
        if len(character) != 1:
            raise ValueError("character must be a single character")
        self.path_char = character
        self.next_nodes.append(target_node)

    def add_epsilon_transition(self, target_node: NFANode) -> None:
        self.next_nodes.append(target_node)

    def __str__(self) -> str:
        next_ids = [str(node.state_id) for node in self.next_nodes]
        char_display = "ε" if self.path_char is None else self.path_char
        return f"State{self.state_id}--[{char_display}]-->{next_ids}"
