from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Mapping, Sequence, Set, Tuple


Symbol = str
RHS = Tuple[Symbol, ...]


@dataclass(frozen=True)
class LL1Sets:
    first: Mapping[Symbol, FrozenSet[Symbol]]
    follow: Mapping[Symbol, FrozenSet[Symbol]]
    select: Mapping[Tuple[Symbol, RHS], FrozenSet[Symbol]]


class LL1Grammar:
    """一个 LL(1) 文法工具：计算 FIRST/FOLLOW/SELECT。

    约定：
    - 非终结符：出现在 productions 的 key 中的符号
    - 终结符：除此之外的一律当作终结符（包含 'EOF'）
    - ε：用空 RHS () 表示
    """

    def __init__(self, start_symbol: Symbol, productions: Mapping[Symbol, Sequence[Sequence[Symbol]]]):
        self.start_symbol = start_symbol
        self.productions: Dict[Symbol, List[RHS]] = {
            lhs: [tuple(rhs) for rhs in rhss] for lhs, rhss in productions.items()
        }

        self.nonterminals: FrozenSet[Symbol] = frozenset(self.productions.keys())

    # 判断符号是否为非终结符
    def is_nonterminal(self, sym: Symbol) -> bool:
        return sym in self.nonterminals

    def terminals(self) -> FrozenSet[Symbol]:
        ts: Set[Symbol] = set()
        for lhs, rhss in self.productions.items():
            for rhs in rhss:
                for sym in rhs:
                    if not self.is_nonterminal(sym):
                        ts.add(sym)
        # 终结符
        return frozenset(ts)

    def compute_first_follow_select(self) -> LL1Sets:
        first = self._compute_first()
        follow = self._compute_follow(first)
        select = self._compute_select(first, follow)
        return LL1Sets(first=first, follow=follow, select=select)

    def _compute_first(self) -> Dict[Symbol, FrozenSet[Symbol]]:
        # FIRST(sym) 只包含终结符；ε 通过 empty rhs 推导时，用特殊标记内部处理。
        EPS = "ε"

        first: Dict[Symbol, Set[Symbol]] = {nt: set() for nt in self.nonterminals}

        changed = True
        while changed:
            changed = False
            for lhs, rhss in self.productions.items():
                for rhs in rhss:
                    if len(rhs) == 0:
                        if EPS not in first[lhs]:
                            first[lhs].add(EPS)
                            changed = True
                        continue

                    # FIRST(rhs1 rhs2 ...)
                    all_can_eps = True
                    for sym in rhs:
                        if self.is_nonterminal(sym):
                            sym_first = first[sym]
                            add_set = {t for t in sym_first if t != EPS}
                            if not add_set.issubset(first[lhs]):
                                first[lhs].update(add_set)
                                changed = True
                            if EPS in sym_first:
                                # 继续看下一个
                                pass
                            else:
                                all_can_eps = False
                                break
                        else:
                            # 终结符
                            if sym not in first[lhs]:
                                first[lhs].add(sym)
                                changed = True
                            all_can_eps = False
                            break

                    if all_can_eps:
                        if EPS not in first[lhs]:
                            first[lhs].add(EPS)
                            changed = True

        return {k: frozenset(v) for k, v in first.items()}

    def _first_of_sequence(self, seq: Sequence[Symbol], first: Mapping[Symbol, FrozenSet[Symbol]]) -> Tuple[Set[Symbol], bool]:
        """返回 (FIRST(seq) 里除 ε 的终结符集合, seq 是否可推出 ε)。"""
        EPS = "ε"
        out: Set[Symbol] = set()
        if len(seq) == 0:
            return out, True

        for sym in seq:
            if self.is_nonterminal(sym):
                f = first[sym]
                out.update(t for t in f if t != EPS)
                if EPS in f:
                    continue
                return out, False
            else:
                out.add(sym)
                return out, False

        return out, True

    def _compute_follow(self, first: Mapping[Symbol, FrozenSet[Symbol]]) -> Dict[Symbol, FrozenSet[Symbol]]:
        follow: Dict[Symbol, Set[Symbol]] = {nt: set() for nt in self.nonterminals}
        follow[self.start_symbol].add("EOF")

        changed = True
        while changed:
            changed = False
            for lhs, rhss in self.productions.items():
                for rhs in rhss:
                    for i, B in enumerate(rhs):
                        if not self.is_nonterminal(B):
                            continue

                        beta = rhs[i + 1 :]
                        first_beta, beta_can_eps = self._first_of_sequence(beta, first)

                        if not first_beta.issubset(follow[B]):
                            follow[B].update(first_beta)
                            changed = True

                        if beta_can_eps:
                            # FOLLOW(B) += FOLLOW(lhs)
                            if not follow[lhs].issubset(follow[B]):
                                follow[B].update(follow[lhs])
                                changed = True

        return {k: frozenset(v) for k, v in follow.items()}

    def _compute_select(
        self,
        first: Mapping[Symbol, FrozenSet[Symbol]],
        follow: Mapping[Symbol, FrozenSet[Symbol]],
    ) -> Dict[Tuple[Symbol, RHS], FrozenSet[Symbol]]:
        select: Dict[Tuple[Symbol, RHS], Set[Symbol]] = {}

        for lhs, rhss in self.productions.items():
            for rhs in rhss:
                first_rhs, rhs_can_eps = self._first_of_sequence(rhs, first)
                s: Set[Symbol] = set(first_rhs)
                if rhs_can_eps:
                    s.update(follow[lhs])
                select[(lhs, rhs)] = frozenset(s)

        return select


def format_ll1_sets(sets: LL1Sets) -> str:
    def fmt_set(items: Sequence[str]) -> str:
        return "{ " + ", ".join(sorted(items)) + " }"

    def rhs_to_str(rhs: RHS) -> str:
        return " ".join(rhs) if rhs else "ε"

    lines: List[str] = []
    lines.append("========================================\n")
    lines.append("     LL(1) FIRST / FOLLOW / SELECT\n")
    lines.append("========================================\n\n")

    nts = sorted(sets.first.keys())

    lines.append("[FIRST]\n")
    for nt in nts:
        lines.append(f"FIRST({nt}) = {fmt_set(list(sets.first[nt]))}\n")
    lines.append("\n")

    lines.append("[FOLLOW]\n")
    for nt in sorted(sets.follow.keys()):
        lines.append(f"FOLLOW({nt}) = {fmt_set(list(sets.follow[nt]))}\n")
    lines.append("\n")

    lines.append("[SELECT]\n")
    # 按 lhs / rhs 排序，保证输出稳定
    items = list(sets.select.items())
    items.sort(key=lambda kv: (kv[0][0], rhs_to_str(kv[0][1])))
    for (lhs, rhs), sel in items:
        lines.append(f"SELECT({lhs} -> {rhs_to_str(rhs)}) = {fmt_set(list(sel))}\n")

    return "".join(lines)


def build_default_ll1_sets() -> LL1Sets:
    """与 [文法(LL1)与SELECT集合.md] 对齐的默认 LL(1) 文法集合。"""
    prods: Dict[Symbol, List[List[Symbol]]] = {
        # Program
        "Program": [["StmtList", "EOF"]],
        "StmtList": [["Stmt", "StmtList"], []],
        "Stmt": [
            ["ForStmt"],
            ["Block"],
            ["DeclStmt", ";"],
            [";"],
            ["PrefixIncDec", ";"],
            ["IDENT", "IdStmtTail", ";"],
        ],
        "Block": [["{", "StmtList", "}"]],
        # for
        "ForStmt": [["for", "(", "ForInitOpt", ";", "ForCondOpt", ";", "ForIterOpt", ")", "Stmt"]],
        "ForInitOpt": [["DeclStmt"], ["PrefixIncDec"], ["IDENT", "ForIdTail"], []],
        "ForCondOpt": [["Expr"], []],
        "ForIterOpt": [["PrefixIncDec"], ["IDENT", "ForIdTail"], []],
        # decl/assign/incdec
        "DeclStmt": [["Type", "IDENT", "DeclInitOpt"]],
        "Type": [["int"], ["float"], ["double"], ["char"]],
        "DeclInitOpt": [["=", "Expr"], []],
        "AssignOp": [["="], ["+="], ["-="], ["*="], ["/="]],
        "IncDecOp": [["++"], ["--"]],
        "PrefixIncDec": [["IncDecOp", "IDENT"]],
        "IdStmtTail": [["IncDecOp"], ["AssignOp", "Expr"]],
        "ForIdTail": [["IncDecOp"], ["AssignOp", "Expr"]],
        # expr (LL(1) form)
        "Expr": [["AddExpr", "RelTail"]],
        "RelTail": [["RelOp", "AddExpr", "RelTail"], []],
        "RelOp": [["<"], ["<="], [">"], [">="], ["=="], ["!="]],
        "AddExpr": [["MulExpr", "AddTail"]],
        "AddTail": [["AddOp", "MulExpr", "AddTail"], []],
        "AddOp": [["+"], ["-"]],
        "MulExpr": [["Unary", "MulTail"]],
        "MulTail": [["MulOp", "Unary", "MulTail"], []],
        "MulOp": [["*"], ["/"]],
        "Unary": [["UnaryOp", "Unary"], ["Primary"]],
        "UnaryOp": [["+"], ["-"], ["!"]],
        "Primary": [["IDENT"], ["NUM"], ["(", "Expr", ")"]],
    }

    grammar = LL1Grammar(start_symbol="Program", productions=prods)
    return grammar.compute_first_follow_select()
