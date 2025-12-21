from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    type: str
    lexeme: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"⟨{self.type}, '{self.lexeme}'⟩ at {self.line}:{self.column}"
