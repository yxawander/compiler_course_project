from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List

from nfa.nfa import NFA
from nfa.nfa_node import NFANode


@dataclass
class NFABuilder:
    """将简化正则（支持 |, *, (), 隐式连接）构建为 Thompson NFA。

    - 中缀转后缀时内部使用连接符 '~' 与结束符 '#'
    - 仅把 '|~*()' 视为运算符；其他字符都当作普通字符
    - 支持转义序列：\\n, \\t, \\r, \\0，以及默认转义（例如 \\| 表示字面量 '|')
    """
    
    # 每创建一个 NFANode 都会 +1
    state_counter: int = 0
    # NFA 栈，在 后缀 转 NFA 过程中使用
    nfa_stack: Deque[NFA] = field(default_factory=deque)
    # 运算符栈，在 中缀 转 后缀 过程中使用
    op_stack: Deque[str] = field(default_factory=deque)

    def _next_state_id(self) -> int:
        self.state_counter += 1
        return self.state_counter

    # 判断是否为运算符
    @staticmethod
    def _is_operator(ch: str) -> bool:
        return ch in "|~*()"
    
    # 运算符优先级
    # *为闭包，~为连接，|为或（注意~是人为假设的）
    @staticmethod
    def _priority(op: str) -> int:
        if op == "*":
            return 3
        if op == "~":
            return 2
        if op == "|":
            return 1
        return 0

    @staticmethod
    def _parse_escape_token(token: str) -> str:
        # token 可能是 "\\n" 或 "a" 或 "\\|"
        if len(token) > 1 and token.startswith("\\"):
            esc = token[1]
            if esc == "n":
                return "\n"
            if esc == "t":
                return "\t"
            if esc == "r":
                return "\r"
            if esc == "0":
                return "\0"
            return esc
        return token[0]

    # 中缀表达式转后缀表达式
    def _infix_to_postfix(self, regex: str) -> List[str]:
        processed = regex + "#"
        output: List[str] = []
        self.op_stack.clear()

        i = 0
        prev_char = "#"  # 记录上一个已处理 token 的类型，用来判断“当前 token 前面是否可以合法连接”，作为初始哨兵（sentinel），表示“还没有处理任何字符”，保证表达式开头不会错误地插入隐式连接符 ~

        while i < len(processed):
            current = processed[i]

            # 1) 处理转义字符
            if current == "\\":
                if prev_char != "#" and (prev_char == ")" or (not self._is_operator(prev_char)) or prev_char == "*"):
                    while self.op_stack and self._priority(self.op_stack[-1]) >= self._priority("~"):
                        output.append(self.op_stack.pop())
                    self.op_stack.append("~")

                if i + 1 < len(processed):
                    escape_seq = "\\" + processed[i + 1]
                    output.append(escape_seq)
                    prev_char = "a"  # 将转义序列视为普通字符
                    i += 2
                else:
                    # 非法：以 \\ 结尾，当作普通 \\ 处理
                    output.append("\\")
                    prev_char = "\\"
                    i += 1
                continue

            # 2) 普通字符
            if current != "#" and not self._is_operator(current):
                if prev_char != "#" and (prev_char == ")" or (not self._is_operator(prev_char)) or prev_char == "*"):
                    while self.op_stack and self._priority(self.op_stack[-1]) >= self._priority("~"):
                        output.append(self.op_stack.pop())
                    self.op_stack.append("~")
                output.append(current)
                prev_char = current
                i += 1
                continue

            # 3) 左括号
            if current == "(":
                if prev_char != "#" and (prev_char == ")" or (not self._is_operator(prev_char)) or prev_char == "*"):
                    while self.op_stack and self._priority(self.op_stack[-1]) >= self._priority("~"):
                        output.append(self.op_stack.pop())
                    self.op_stack.append("~")
                self.op_stack.append(current)
                prev_char = current
                i += 1
                continue

            # 4) 右括号
            if current == ")":
                while self.op_stack and self.op_stack[-1] != "(":
                    output.append(self.op_stack.pop())
                if self.op_stack and self.op_stack[-1] == "(":
                    self.op_stack.pop()
                else:
                    raise ValueError(f"Unmatched parentheses in regex: {regex}")
                prev_char = current
                i += 1
                continue

            # 5) 结束符 '#'
            if current == "#":
                while self.op_stack:
                    op = self.op_stack.pop()
                    if op == "(":
                        raise ValueError("Unmatched parentheses in regex")
                    output.append(op)
                i += 1
                continue

            # 6) 运算符 | *
            while self.op_stack and self._priority(self.op_stack[-1]) >= self._priority(current) and self.op_stack[-1] != "(":
                output.append(self.op_stack.pop())
            self.op_stack.append(current)
            prev_char = current
            i += 1

        return output

    def _meet_non_symbol(self, ch: str) -> NFA:
        start = NFANode(self._next_state_id())
        end = NFANode(self._next_state_id())
        start.add_transition(ch, end)
        return NFA(start, end)

    def _meet_or(self, a: NFA, b: NFA) -> NFA:
        new_start = NFANode(self._next_state_id())
        new_end = NFANode(self._next_state_id())
        new_start.add_epsilon_transition(a.start_node)
        new_start.add_epsilon_transition(b.start_node)
        a.end_node.add_epsilon_transition(new_end)
        b.end_node.add_epsilon_transition(new_end)
        return NFA(new_start, new_end)

    @staticmethod
    def _meet_and(a: NFA, b: NFA) -> NFA:
        a.end_node.add_epsilon_transition(b.start_node)
        return NFA(a.start_node, b.end_node)

    def _meet_star(self, old: NFA) -> NFA:
        new_start = NFANode(self._next_state_id())
        new_end = NFANode(self._next_state_id())
        new_start.add_epsilon_transition(new_end)
        new_start.add_epsilon_transition(old.start_node)
        old.end_node.add_epsilon_transition(old.start_node)
        old.end_node.add_epsilon_transition(new_end)
        return NFA(new_start, new_end)

    def build_nfa(self, regex: str) -> NFA:
        if regex is None or regex == "":
            raise ValueError("Regex cannot be null or empty")

        postfix = self._infix_to_postfix(regex)
        self.nfa_stack.clear()
        self.state_counter = 0

        for token in postfix:
            # token 可能是运算符，也可能是 "\\+" 这种转义 token
            if (not self._is_operator(token[0])) or token.startswith("\\"):
                ch = self._parse_escape_token(token)
                self.nfa_stack.append(self._meet_non_symbol(ch))
                continue

            op = token[0]
            if op == "|":
                if len(self.nfa_stack) < 2:
                    raise ValueError("Invalid regex: missing operands for |")
                b = self.nfa_stack.pop()
                a = self.nfa_stack.pop()
                self.nfa_stack.append(self._meet_or(a, b))
            elif op == "~":
                if len(self.nfa_stack) < 2:
                    raise ValueError("Invalid regex: missing operands for concatenation")
                b = self.nfa_stack.pop()
                a = self.nfa_stack.pop()
                self.nfa_stack.append(self._meet_and(a, b))
            elif op == "*":
                if not self.nfa_stack:
                    raise ValueError("Invalid regex: missing operand for *")
                old = self.nfa_stack.pop()
                self.nfa_stack.append(self._meet_star(old))
            else:
                raise ValueError(f"Unsupported operator: {op}")

        if len(self.nfa_stack) != 1:
            raise ValueError(f"Invalid regex expression: {regex}")

        return self.nfa_stack.pop()

if __name__ == "__main__":
    builder = NFABuilder()
    regex = "a(b|c)*d"
    postfix = builder._infix_to_postfix(regex)
    print("中缀表达式:", regex)
    print("后缀表达式:", postfix)