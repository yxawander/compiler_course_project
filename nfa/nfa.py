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
    
    def visualize(self) -> None:
        """打印 NFA 的所有状态和转移关系"""
        visited = set()
        queue = [self.start_node]
        print("NFA 状态转移：")
        while queue:
            node = queue.pop(0)
            if node.state_id in visited:
                continue
            visited.add(node.state_id)
            print(str(node))
            for next_node in node.next_nodes:
                if next_node.state_id not in visited:
                    queue.append(next_node)