from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class ParseError(Exception):
    message: str
    line: int
    column: int
    # 实际得到的符号
    got: str
    # 期望得到的符号列表
    expected: Optional[Iterable[str]] = None

    def __str__(self) -> str:
        exp = ""
        if self.expected:
            exp = f"，期望: {', '.join(sorted(set(self.expected)))}"
        return f"语法错误 @ 行{self.line},列{self.column}: {self.message}（得到: {self.got}{exp}）"


@dataclass
class SemanticError(Exception):
    message: str
    line: int
    column: int
    # 相关符号（如标识符/运算符）
    symbol: str

    def __str__(self) -> str:
        return f"语义错误 @ 行{self.line},列{self.column}: {self.message}（符号: {self.symbol}）"
