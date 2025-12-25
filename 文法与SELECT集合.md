# LL(1) 文法

---

## 终结符（terminal）

- 关键字：`for`、`int`、`float`、`double`、`char`
- 标识符/常量：`IDENT`、`NUM`
- 分隔符：`(` `)` `{` `}` `;`
- 运算符：
  - 赋值：`=` `+=` `-=` `*=` `/=`
  - 自增自减：`++` `--`
  - 关系：`<` `<=` `>` `>=` `==` `!=`
  - 加乘：`+` `-` `*` `/`
  - 一元：`+` `-` `!`

---

## 非终结符（non-terminal）

`Program, StmtList, Stmt, Block, ForStmt, ForInitOpt, ForCondOpt, ForIterOpt, DeclStmt, DeclInitOpt, AssignOp, IncDecOp, PrefixIncDec, IdStmtTail, ForIdTail, Expr, RelTail, AddExpr, AddTail, MulExpr, MulTail, Unary, Primary`

---

## LL(1) 文法

### 程序与语句

1. `Program -> StmtList EOF`
2. `StmtList -> Stmt StmtList | ε`
3. `Stmt -> ForStmt | Block | DeclStmt ';' | ';' | PrefixIncDec ';' | IDENT IdStmtTail ';'`
4. `Block -> '{' StmtList '}'`

> 说明：这里把“IDENT 起始语句”的冲突做了**因子分解**：
>
> - 若语句以 `IDENT` 开头，只需再看 1 个 lookahead（下一符号是 `IncDecOp` 还是 `AssignOp`）即可选择。
> - 项目代码里目前是直接在 `Stmt` 分支里用 `peek(1)` 做同等效果。

### for 语句

5. `ForStmt -> 'for' '(' ForInitOpt ';' ForCondOpt ';' ForIterOpt ')' Stmt`
6. `ForInitOpt -> DeclStmt | PrefixIncDec | IDENT ForIdTail | ε`
7. `ForCondOpt -> Expr | ε`
8. `ForIterOpt -> PrefixIncDec | IDENT ForIdTail | ε`

### 声明/赋值/自增自减

9. `DeclStmt -> Type IDENT DeclInitOpt`
10. `Type -> 'int' | 'float' | 'double' | 'char'`
11. `DeclInitOpt -> '=' Expr | ε`
12. `AssignOp -> '=' | '+=' | '-=' | '*=' | '/='`
13. `IncDecOp -> '++' | '--'`
14. `PrefixIncDec -> IncDecOp IDENT`
15. `IdStmtTail -> IncDecOp | AssignOp Expr`
16. `ForIdTail -> IncDecOp | AssignOp Expr`

### 表达式（优先级）

17. `Expr -> AddExpr RelTail`
18. `RelTail -> RelOp AddExpr RelTail | ε`
19. `RelOp -> '<' | '<=' | '>' | '>=' | '==' | '!='`
20. `AddExpr -> MulExpr AddTail`
21. `AddTail -> AddOp MulExpr AddTail | ε`
22. `AddOp -> '+' | '-'`
23. `MulExpr -> Unary MulTail`
24. `MulTail -> MulOp Unary MulTail | ε`
25. `MulOp -> '*' | '/'`
26. `Unary -> UnaryOp Unary | Primary`
27. `UnaryOp -> '+' | '-' | '!'`
28. `Primary -> IDENT | NUM | '(' Expr ')'`

---

## 关键 FIRST/SELECT 集合

> 说明：项目代码已支持 **自动计算 FIRST/FOLLOW/SELECT**。
>
> - 计算逻辑在 `parser/ll1_sets.py`（`build_default_ll1_sets()`）
> - 主程序运行时会额外导出一个文本文件：`{源文件名}_FIRST_FOLLOW_SELECT.txt`
>
> 下面仍保留关键集合的手工推导结果，便于对照验证。

### FIRST(Expr)

- `FIRST(Expr) = { IDENT, NUM, '(', '+', '-', '!' }`

### ForCondOpt 的 SELECT

- `SELECT(ForCondOpt -> Expr) = FIRST(Expr)`
- `SELECT(ForCondOpt -> ε) = { ';' }`

### ForIterOpt 的 SELECT

- `SELECT(ForIterOpt -> PrefixIncDec) = { '++', '--' }`
- `SELECT(ForIterOpt -> IDENT ForIdTail) = { 'IDENT' }`
- `SELECT(ForIterOpt -> ε) = { ')' }`

### ForIdTail / IdStmtTail 的 SELECT

- `SELECT(ForIdTail -> IncDecOp) = { '++', '--' }`
- `SELECT(ForIdTail -> AssignOp Expr) = { '=', '+=', '-=', '*=', '/=' }`

（`IdStmtTail` 同理，与 `ForIdTail` 一致）

### Stmt 的 SELECT

- `SELECT(Stmt -> ForStmt) = { 'for' }`
- `SELECT(Stmt -> Block) = { '{' }`
- `SELECT(Stmt -> DeclStmt ';') = { 'int','float','double','char' }`
- `SELECT(Stmt -> ';') = { ';' }`
- `SELECT(Stmt -> PrefixIncDec ';') = { '++','--' }`
- `SELECT(Stmt -> IDENT IdStmtTail ';') = { 'IDENT' }`

---

## 与代码对应的位置

- 递归下降解析器：parser/rd_parser.py
  - SELECT/FIRST 的使用点：文件顶部 `_FIRST_EXPR` / `_SELECT_*`（**由自动计算结果生成**）
  - for 的三段选择：`RDParser._for_stmt()`
  - 语句选择：`RDParser._stmt()`

- LL(1) 集合自动计算：parser/ll1_sets.py
  - FIRST/FOLLOW/SELECT 计算：`LL1Grammar.compute_first_follow_select()`
  - 默认文法（与本文对齐）：`build_default_ll1_sets()`

- 集合导出文件：main.py
  - 输出路径：`{源文件名}_FIRST_FOLLOW_SELECT.txt`
