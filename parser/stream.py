from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..lexer.token import Token


@dataclass(frozen=True)
class SyntaxToken:
    terminal: str
    lexeme: str
    line: int
    column: int
    raw_type: str

    @staticmethod
    def from_lex_token(tok: Token) -> "SyntaxToken":
        # 终结符归一化：关键字/运算符/分隔符用 lexeme；标识符与数值用类别。
        if tok.type == "KEYWORD":
            terminal = tok.lexeme
        elif tok.type == "IDENTIFIER":
            terminal = "IDENT"
        elif tok.type in {"INTEGER", "FLOAT"}:
            terminal = "NUM"
        # 运算符和分隔符
        elif tok.type in {"OPERATOR", "DELIMITER"}:
            terminal = tok.lexeme
        elif tok.type == "STRING":
            terminal = "STRING"
        elif tok.type == "ERROR":
            terminal = "ERROR"
        else:
            terminal = tok.type
        return SyntaxToken(terminal=terminal, lexeme=tok.lexeme, line=tok.line, column=tok.column, raw_type=tok.type)


class TokenStream:
    def __init__(self, tokens: List[SyntaxToken]):
        self._tokens = tokens
        # 当前读到哪一个 token 的索引
        self._i = 0

    # 看 k 个 token 之后的 token，k=0 表示当前 token，但是不会移动读取位置
    def peek(self, k: int = 0) -> SyntaxToken:
        idx = self._i + k
        if idx < 0:
            idx = 0
        if idx >= len(self._tokens):
            return self._tokens[-1]
        return self._tokens[idx]

    # 返回当前 token，移动到下一个 token
    def advance(self) -> SyntaxToken:
        tok = self.peek(0)
        if self._i < len(self._tokens) - 1:
            self._i += 1
        return tok

    def at_end(self) -> bool:
        return self.peek().terminal == "EOF"

    def index(self) -> int:
        return self._i

    def set_index(self, i: int) -> None:
        self._i = max(0, min(i, len(self._tokens) - 1))


def normalize_tokens(lex_tokens: List[Token], drop_error_tokens: bool = True) -> List[SyntaxToken]:
    out: List[SyntaxToken] = []
    for t in lex_tokens:
        if drop_error_tokens and t.type == "ERROR":
            continue
        out.append(SyntaxToken.from_lex_token(t))
    # EOF 哨兵
    if out:
        last = out[-1]
        eof_line, eof_col = last.line, last.column + max(1, len(last.lexeme))
    else:
        eof_line, eof_col = 1, 1
    out.append(SyntaxToken(terminal="EOF", lexeme="", line=eof_line, column=eof_col, raw_type="EOF"))
    return out
