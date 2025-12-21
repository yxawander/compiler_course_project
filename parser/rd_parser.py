from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Set, Tuple

from parser.errors import ParseError
from parser.stream import SyntaxToken, TokenStream
from parser.tac import TACEmitter


_TYPE_KEYWORDS = {"int", "float", "double", "char"}
_REL_OPS = {"<", "<=", ">", ">=", "==", "!="}
_ADD_OPS = {"+", "-"}
_MUL_OPS = {"*", "/"}
_ASSIGN_OPS = {"=", "+=", "-=", "*=", "/="}


@dataclass(frozen=True)
class ParseResult:
    ok: bool
    errors: List[ParseError]
    parse_trace: List[str]
    sem_trace: List[str]
    emitter: TACEmitter


class RDParser:
    def __init__(self, stream: TokenStream):
        self.s = stream
        self.errors: List[ParseError] = []
        self.parse_trace: List[str] = []
        self._indent = 0
        self.emitter = TACEmitter()

        # 展示用：是否输出“赋值语句教材格式分析表”到 parse_trace
        self.enable_assign_table = True

    def parse_program(self) -> ParseResult:
        self._enter("Program")
        try:
            self._stmt_list(stop_terminals={"EOF"})
            self._expect("EOF")
            ok = len(self.errors) == 0
        except ParseError as e:
            self.errors.append(e)
            ok = False
        finally:
            self._leave("Program")

        return ParseResult(
            ok=ok,
            errors=self.errors,
            parse_trace=self.parse_trace,
            sem_trace=list(self.emitter.trace),
            emitter=self.emitter,
        )

    # ---------------- trace helpers ----------------
    def _log(self, msg: str) -> None:
        self.parse_trace.append("  " * self._indent + msg)

    def _enter(self, name: str) -> None:
        self._log(f"进入 <{name}>")
        self._indent += 1

    def _leave(self, name: str) -> None:
        self._indent = max(0, self._indent - 1)
        self._log(f"退出 <{name}>")

    # ---------------- token helpers ----------------
    def _peek(self) -> SyntaxToken:
        return self.s.peek(0)

    def _match(self, terminal: str) -> Optional[SyntaxToken]:
        if self._peek().terminal == terminal:
            tok = self.s.advance()
            self._log(f"match {terminal} ({tok.lexeme})")
            return tok
        return None

    def _expect(self, terminal: str) -> SyntaxToken:
        tok = self._peek()
        if tok.terminal != terminal:
            raise ParseError(
                message="终结符不匹配",
                line=tok.line,
                column=tok.column,
                got=tok.terminal or tok.lexeme,
                expected=[terminal],
            )
        return self.s.advance()

    def _expect_any(self, terminals: Sequence[str]) -> SyntaxToken:
        tok = self._peek()
        if tok.terminal not in terminals:
            raise ParseError(
                message="终结符不匹配",
                line=tok.line,
                column=tok.column,
                got=tok.terminal or tok.lexeme,
                expected=list(terminals),
            )
        self._log(f"match {tok.terminal} ({tok.lexeme})")
        return self.s.advance()

    def _sync_to(self, sync: Set[str]) -> None:
        # 简单恐慌模式：跳过直到遇到同步集合中的 token 或 EOF
        while self._peek().terminal not in sync and self._peek().terminal != "EOF":
            self.s.advance()

    # ---------------- assign stmt analysis table (textbook style) ----------------
    @staticmethod
    def _stmt_lexemes(tokens: List[SyntaxToken]) -> str:
        return "".join(t.lexeme for t in tokens if t.terminal != "EOF")

    @staticmethod
    def _lookahead_symbol(tok: SyntaxToken) -> str:
        # 表格里“分析字符”显示具体字符：id/num 用 lexeme，其余用 lexeme
        if tok.terminal in {"IDENT", "NUM"}:
            return tok.lexeme
        if tok.terminal == "EOF":
            return "EOF"
        return tok.lexeme

    @staticmethod
    def _terminal_kind(tok: SyntaxToken) -> str:
        # 表达式预测分析用的“终结符种类”
        if tok.terminal == "IDENT":
            return "id"
        if tok.terminal == "NUM":
            return "num"
        if tok.terminal == "EOF":
            return "EOF"
        return tok.terminal  # '+', '-', '*', '/', '(', ')', ';', '=' 等

    def _collect_assign_stmt_tokens(self, require_semicolon: bool, limit: int = 200) -> List[SyntaxToken]:
        # 从当前 token 起，向后收集到 ';'（包含）为止，用于生成分析表；不移动流位置
        out: List[SyntaxToken] = []
        for k in range(limit):
            t = self.s.peek(k)
            out.append(t)
            if t.terminal == "EOF":
                break
            if require_semicolon and t.terminal == ";":
                break
        return out

    def _build_assign_table_text(self, stmt_tokens: List[SyntaxToken]) -> List[str]:
        # 只对形如：IDENT (ASSIGN_OP) Expr ; 的语句生成“纯文本四列表格”
        # 文法使用：S -> id op Expr ;，Expr -> Term ExprP，Term -> Factor TermP
        if len(stmt_tokens) < 4:
            return []

        # 基本结构检查
        if stmt_tokens[0].terminal != "IDENT":
            return []

        op_lexeme = stmt_tokens[1].lexeme
        if stmt_tokens[1].terminal not in _ASSIGN_OPS:
            # 兼容某些情况下 terminal 可能就是 '=' 这样的 lexeme
            if stmt_tokens[1].lexeme not in _ASSIGN_OPS:
                return []
            op_lexeme = stmt_tokens[1].lexeme

        # 找到分号，截断（确保剩余串展示一致）
        end_idx = None
        for i, t in enumerate(stmt_tokens):
            if t.terminal == ";":
                end_idx = i
                break
        if end_idx is None:
            return []
        stmt_tokens = stmt_tokens[: end_idx + 1]

        full_stmt = self._stmt_lexemes(stmt_tokens)
        lhs = stmt_tokens[0].lexeme

        # 输入指针 i 指向当前 lookahead
        i = 0
        consumed = ""  # 分析串

        def remaining() -> str:
            return "".join(t.lexeme for t in stmt_tokens[i:])

        rows: List[List[str]] = []

        def add_row(prod: str) -> None:
            la = stmt_tokens[i] if i < len(stmt_tokens) else SyntaxToken("EOF", "", 0, 0, "EOF")
            rows.append([prod, consumed, self._lookahead_symbol(la), remaining()])

        # 1) S -> id op Expr ;
        add_row(f"S -> id {op_lexeme} Expr ;")

        # 隐式 match: id 与 op
        consumed += stmt_tokens[0].lexeme
        i += 1
        consumed += stmt_tokens[1].lexeme
        i += 1

        # 预测分析栈（只用于驱动产生式选择，不输出）
        stack: List[str] = [";", "Expr"]

        def kind() -> str:
            if i >= len(stmt_tokens):
                return "EOF"
            return self._terminal_kind(stmt_tokens[i])

        while stack:
            top = stack.pop()
            la_kind = kind()

            if top == ";":
                # 匹配分号
                if la_kind == ";":
                    consumed += stmt_tokens[i].lexeme
                    i += 1
                    continue
                # 不匹配就停止生成表
                break

            if top == "Expr":
                add_row("Expr -> Term ExprP")
                stack.extend(["ExprP", "Term"])
                continue

            if top == "ExprP":
                if la_kind in {"+", "-"}:
                    op = la_kind
                    add_row(f"ExprP -> {op} Term ExprP")
                    # 产生式右部：op Term ExprP
                    stack.extend(["ExprP", "Term", op])
                    continue
                if la_kind in {")", ";", "EOF"}:
                    add_row("ExprP -> ε")
                    continue
                break

            if top == "Term":
                add_row("Term -> Factor TermP")
                stack.extend(["TermP", "Factor"])
                continue

            if top == "TermP":
                if la_kind in {"*", "/"}:
                    op = la_kind
                    add_row(f"TermP -> {op} Factor TermP")
                    stack.extend(["TermP", "Factor", op])
                    continue
                if la_kind in {"+", "-", ")", ";", "EOF"}:
                    add_row("TermP -> ε")
                    continue
                break

            if top == "Factor":
                if la_kind == "id":
                    add_row("Factor -> id")
                    # 匹配 id
                    consumed += stmt_tokens[i].lexeme
                    i += 1
                    continue
                if la_kind == "num":
                    add_row("Factor -> num")
                    consumed += stmt_tokens[i].lexeme
                    i += 1
                    continue
                if la_kind == "(":
                    add_row("Factor -> ( Expr )")
                    # 推入 ) Expr (
                    stack.extend([")", "Expr", "("])
                    continue
                break

            # 终结符：+ - * / ( )
            if top in {"+", "-", "*", "/", "(", ")"}:
                if la_kind == top:
                    consumed += stmt_tokens[i].lexeme
                    i += 1
                    continue
                break

            # 兜底：未知符号
            break

        if not rows:
            return []

        # 组装纯文本四列表格（不使用 Markdown 分隔线/标题语法）
        # 按用户要求：只有表头那一行保留竖线；数据行用空格对齐拉开列间距。
        out: List[str] = []
        out.append("")
        out.append(f"【赋值语句分析表】{full_stmt}")

        # 表头：只保留这一行竖线
        out.append("文法 | 分析串 | 分析字符 | 剩余串")

        # 数据行：固定宽度 + 多空格分隔
        col1_w = 22  # 文法
        col2_w = 10  # 分析串
        col3_w = 8   # 分析字符
        gap = " " * 6
        for prod, ana, ch, rem in rows:
            out.append(
                f"{prod:<{col1_w}}{gap}"
                f"{ana:<{col2_w}}{gap}"
                f"{ch:<{col3_w}}{gap}"
                f"{rem}"
            )
        out.append("")
        return out

    # ---------------- grammar ----------------
    def _stmt_list(self, stop_terminals: Set[str]) -> None:
        self._enter("StmtList")
        while self._peek().terminal not in stop_terminals:
            if self._peek().terminal == "EOF":
                break
            self._stmt()
        self._leave("StmtList")

    def _stmt(self) -> None:
        self._enter("Stmt")
        tok = self._peek()
        try:
            if tok.terminal == "for":
                self._for_stmt()
            elif tok.terminal == "{":
                self._block()
            elif tok.terminal in _TYPE_KEYWORDS:
                # 声明语句
                self._decl_stmt(require_semicolon=True)
            elif tok.terminal == ";":
                self._expect(";")
            elif tok.terminal == "IDENT":
                if self.s.peek(1).terminal in {"++", "--"}:
                    # 自增自减语句
                    self._incdec(require_semicolon=True)
                else:
                    # 赋值语句
                    self._assign_stmt(require_semicolon=True)
            else:
                raise ParseError(
                    message="无法识别的语句起始符",
                    line=tok.line,
                    column=tok.column,
                    got=tok.terminal,
                    expected=["for", "{", ";", "IDENT"] + sorted(_TYPE_KEYWORDS),
                )
        except ParseError as e:
            self.errors.append(e)
            self._log(str(e))
            # 恢复：跳过到 ; 或 } 或 EOF
            self._sync_to({";", "}", "EOF"})
            if self._peek().terminal == ";":
                self.s.advance()
        finally:
            self._leave("Stmt")

    def _block(self) -> None:
        self._enter("Block")
        self._expect("{")
        self._stmt_list(stop_terminals={"}"})
        self._expect("}")
        self._leave("Block")

    def _for_stmt(self) -> None:
        self._enter("ForStmt")
        self._expect("for")
        self._expect("(")

        # init
        if self._peek().terminal in _TYPE_KEYWORDS:
            self._decl_stmt(require_semicolon=False)
        elif self._peek().terminal == "IDENT":
            # assign or inc/dec
            if self.s.peek(1).terminal in {"++", "--"}:
                self._incdec(require_semicolon=False)
            else:
                self._assign_stmt(require_semicolon=False)
        # else epsilon
        self._expect(";")

        # cond
        # 条件可选
        cond_tokens: List[SyntaxToken] = []
        if self._peek().terminal != ";":
            while self._peek().terminal not in {";", "EOF"}:
                cond_tokens.append(self.s.advance())
        self._expect(";")

        # iter
        # 我们先“记住”迭代表达式的位置，等 body 解析完再回来生成 iter 的代码。
        iter_tokens: List[SyntaxToken] = []
        if self._peek().terminal != ")":
            while self._peek().terminal not in {")", "EOF"}:
                iter_tokens.append(self.s.advance())
        self._expect(")")

        # codegen skeleton
        L_begin = self.emitter.new_label()
        L_end = self.emitter.new_label()

        # begin
        self.emitter.emit_label(L_begin)

        # cond: 每轮循环都在 L_begin 后重新计算条件
        if cond_tokens:
            last = cond_tokens[-1]
            eof_tok = SyntaxToken(
                terminal="EOF",
                lexeme="",
                line=last.line,
                column=last.column + max(1, len(last.lexeme)),
                raw_type="EOF",
            )
            tmp_stream = TokenStream(cond_tokens + [eof_tok])
            cond_parser = RDParser(tmp_stream)
            cond_parser.emitter = self.emitter  # 共享 emitter
            cond_place = cond_parser._expr()
            self.emitter.emit_if_false(cond_place, L_end)

        # body
        self._stmt()
        
        # 这里没看

        # iter: 回到 iter 片段重新解析并生成代码
        if iter_tokens:
            saved_i = self.s.index()
            # 构造临时 stream 解析 iter
            tmp_stream = TokenStream(iter_tokens + [SyntaxToken("EOF", "", iter_tokens[-1].line, iter_tokens[-1].column, "EOF")])
            iter_parser = RDParser(tmp_stream)
            iter_parser.emitter = self.emitter  # 共享 emitter
            # 只允许 IncDec 或 AssignExpr
            if tmp_stream.peek().terminal == "IDENT" and tmp_stream.peek(1).terminal in {"++", "--"}:
                iter_parser._incdec(require_semicolon=False)
            elif tmp_stream.peek().terminal == "IDENT":
                iter_parser._assign_stmt(require_semicolon=False)
            elif tmp_stream.peek().terminal in {"++", "--"}:
                iter_parser._incdec(require_semicolon=False)
            # 忽略 iter_parser 的 parse_trace/errors（iter 语法错会在主流程暴露为不支持）
            self.s.set_index(saved_i)

        self.emitter.emit_goto(L_begin)
        self.emitter.emit_label(L_end)

        self._leave("ForStmt")

    def _decl_stmt(self, require_semicolon: bool) -> None:
        self._enter("DeclStmt")
        type_tok = self._expect_any(sorted(_TYPE_KEYWORDS))
        ident = self._expect("IDENT")

        if self._match("=") is not None:
            rhs = self._expr()
            self.emitter.emit("=", rhs, "", ident.lexeme)

        if require_semicolon:
            self._expect(";")
        self._leave("DeclStmt")

    def _assign_stmt(self, require_semicolon: bool) -> None:
        self._enter("AssignStmt")
        # 先“偷看”本条赋值语句的 token 串，生成教材格式分析表（不影响真正解析）
        table_lines: List[str] = []
        if self.enable_assign_table and require_semicolon:
            stmt_tokens = self._collect_assign_stmt_tokens(require_semicolon=require_semicolon)
            table_lines = self._build_assign_table_text(stmt_tokens)

        self._assign_expr()
        if require_semicolon:
            self._expect(";")

        # 解析完成后再把表格写到日志里（更好对齐上下文）
        if table_lines:
            self.parse_trace.extend(table_lines)
        self._leave("AssignStmt")

    def _assign_expr(self) -> str:
        self._enter("AssignExpr")
        ident = self._expect("IDENT")
        op_tok = self._expect_any(sorted(_ASSIGN_OPS))
        rhs = self._expr()

        if op_tok.terminal == "=":
            self.emitter.emit("=", rhs, "", ident.lexeme)
        else:
            # x += y 等价于 x = x + y
            mapping = {"+=": "+", "-=": "-", "*=": "*", "/=": "/"}
            arith = mapping[op_tok.terminal]
            t = self.emitter.new_temp()
            self.emitter.emit(arith, ident.lexeme, rhs, t)
            self.emitter.emit("=", t, "", ident.lexeme)

        self._leave("AssignExpr")
        return ident.lexeme

    def _incdec(self, require_semicolon: bool) -> None:
        self._enter("IncDec")
        # 支持 i++ / i-- / ++i / --i
        if self._peek().terminal in {"++", "--"}:
            op = self.s.advance().terminal
            ident = self._expect("IDENT")
        else:
            ident = self._expect("IDENT")
            op = self._expect_any(["++", "--"]).terminal

        one = "1"
        t = self.emitter.new_temp()
        if op == "++":
            self.emitter.emit("+", ident.lexeme, one, t)
        else:
            self.emitter.emit("-", ident.lexeme, one, t)
        self.emitter.emit("=", t, "", ident.lexeme)

        if require_semicolon:
            self._expect(";")
        self._leave("IncDec")

    # ---------------- expr ----------------
    def _expr(self) -> str:
        self._enter("Expr")
        left = self._add_expr()
        # 允许 relop 链（展示用），实际常见只写一次
        while self._peek().terminal in _REL_OPS:
            op = self.s.advance().terminal
            right = self._add_expr()
            t = self.emitter.new_temp()
            self.emitter.emit(op, left, right, t)
            left = t
        self._leave("Expr")
        return left

    def _add_expr(self) -> str:
        self._enter("AddExpr")
        left = self._mul_expr()
        while self._peek().terminal in _ADD_OPS:
            op = self.s.advance().terminal
            right = self._mul_expr()
            t = self.emitter.new_temp()
            self.emitter.emit(op, left, right, t)
            left = t
        self._leave("AddExpr")
        return left

    def _mul_expr(self) -> str:
        self._enter("MulExpr")
        left = self._unary()
        while self._peek().terminal in _MUL_OPS:
            op = self.s.advance().terminal
            right = self._unary()
            t = self.emitter.new_temp()
            self.emitter.emit(op, left, right, t)
            left = t
        self._leave("MulExpr")
        return left

    def _unary(self) -> str:
        self._enter("Unary")
        if self._peek().terminal in {"+", "-", "!"}:
            op = self.s.advance().terminal
            x = self._unary()
            # 一元 + 直接返回；- 与 ! 生成临时
            if op == "+":
                self._leave("Unary")
                return x
            t = self.emitter.new_temp()
            if op == "-":
                self.emitter.emit("-", "0", x, t)
            else:
                # !x 记作 t = ! x（作为四元式打印用）
                self.emitter.emit("!", x, "", t)
            self._leave("Unary")
            return t

        place = self._primary()
        self._leave("Unary")
        return place

    def _primary(self) -> str:
        self._enter("Primary")
        tok = self._peek()
        if tok.terminal == "IDENT":
            t = self.s.advance()
            self._log(f"match IDENT ({t.lexeme})")
            self._leave("Primary")
            return t.lexeme
        if tok.terminal == "NUM":
            t = self.s.advance()
            self._log(f"match NUM ({t.lexeme})")
            self._leave("Primary")
            return t.lexeme
        if tok.terminal == "(":
            self._expect("(")
            x = self._expr()
            self._expect(")")
            self._leave("Primary")
            return x

        raise ParseError(
            message="表达式缺少操作数",
            line=tok.line,
            column=tok.column,
            got=tok.terminal,
            expected=["IDENT", "NUM", "("],
        )
