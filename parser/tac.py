from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


# 四元式数据结构
@dataclass(frozen=True)
class Quad:
    op: str
    arg1: str
    arg2: str
    result: str

    def format_three_address(self) -> str:
        # 统一展示为三地址/控制流形式
        if self.op == "label":
            return f"{self.result}:"
        if self.op == "goto":
            return f"goto {self.result}"
        if self.op == "ifFalse":
            return f"ifFalse {self.arg1} goto {self.result}"
        if self.op == "if":
            # arg1: left, arg2: relop right (打包) 或直接条件
            return f"if {self.arg1} goto {self.result}"
        if self.op in {"=", "+", "-", "*", "/", "<", "<=", ">", ">=", "==", "!="}:
            if self.op == "=":
                return f"{self.result} = {self.arg1}"
            return f"{self.result} = {self.arg1} {self.op} {self.arg2}"
        return f"({self.op}, {self.arg1}, {self.arg2}, {self.result})"

# 三地址码/四元式生成器
class TACEmitter:
    def __init__(self) -> None:
        self.quads: List[Quad] = []
        self.trace: List[str] = []
        self._temp_id = 0
        self._label_id = 0

    def new_temp(self) -> str:
        self._temp_id += 1
        return f"t{self._temp_id}"

    def new_label(self) -> str:
        self._label_id += 1
        return f"L{self._label_id}"

    def emit(self, op: str, arg1: str = "", arg2: str = "", result: str = "") -> None:
        q = Quad(op=op, arg1=arg1, arg2=arg2, result=result)
        self.quads.append(q)
        self.trace.append(q.format_three_address())

    # 特定操作的便捷方法
    def emit_label(self, label: str) -> None:
        self.emit("label", result=label)

    def emit_goto(self, label: str) -> None:
        self.emit("goto", result=label)

    def emit_if_false(self, cond_place: str, label: str) -> None:
        self.emit("ifFalse", arg1=cond_place, result=label)

    # ---------------- backpatch helpers (拉链回填) ----------------
    def emit_goto_placeholder(self) -> int:
        """生成一个目标未确定的 goto，返回该四元式在 quads 中的下标。"""
        self.emit("goto", result="")
        return len(self.quads) - 1

    def emit_if_false_placeholder(self, cond_place: str) -> int:
        """生成一个目标未确定的 ifFalse，返回该四元式在 quads 中的下标。"""
        self.emit("ifFalse", arg1=cond_place, result="")
        return len(self.quads) - 1

    @staticmethod
    def merge_patch_lists(*lists: Iterable[int]) -> List[int]:
        out: List[int] = []
        for lst in lists:
            out.extend(list(lst))
        return out

    def backpatch(self, patch_list: Iterable[int], label: str) -> None:
        """把 patch_list 中的跳转目标统一回填为 label。

        约定：patch_list 存的是 self.quads 的下标。
        """
        for idx in patch_list:
            if idx < 0 or idx >= len(self.quads):
                continue
            q = self.quads[idx]
            if q.op not in {"goto", "ifFalse", "if"}:
                continue
            patched = Quad(op=q.op, arg1=q.arg1, arg2=q.arg2, result=label)
            self.quads[idx] = patched
            # 同步语义日志（RDParser 用 emitter.trace 输出）
            if 0 <= idx < len(self.trace):
                self.trace[idx] = patched.format_three_address()

    def as_text(self) -> str:
        lines: List[str] = []
        lines.append("========================================\n")
        lines.append("           三地址码\n")
        lines.append("========================================\n\n")
        for i, q in enumerate(self.quads, start=1):
            lines.append(f"{i:04d}: {q.format_three_address()}\n")
        return "".join(lines)

    def as_quads_text(self) -> str:
        lines: List[str] = []
        lines.append("========================================\n")
        lines.append("               四元式\n")
        lines.append("========================================\n\n")
        for i, q in enumerate(self.quads, start=1):
            lines.append(f"{i:04d}: ({q.op}, {q.arg1}, {q.arg2}, {q.result})\n")
        return "".join(lines)
