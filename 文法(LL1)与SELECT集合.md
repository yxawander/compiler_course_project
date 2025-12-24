# LL(1) 文法（与本项目递归下降实现对应）

> 目标：给出一个适合“预测分析/递归下降（SELECT 集合选产生式）”的 LL(1) 文法，并说明关键 SELECT 集合。
> 
> 说明：本项目里对 `IDENT` 起始语句需要 **再看 1 个 token（lookahead 2）** 才能区分 `Assign` 和 `IncDec`，这可以通过“因子分解（把 IDENT 先归到同一个产生式，再在尾部用 1 个 lookahead 选择）”来满足 LL(1) 的定义。

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

`Program, StmtList, Stmt, Block, ForStmt, ForInitOpt, ForCondOpt, ForIterOpt,
DeclStmt, DeclInitOpt, AssignOp, IncDecOp, PrefixIncDec, IdStmtTail, ForIdTail,
Expr, RelTail, AddExpr, AddTail, MulExpr, MulTail, Unary, Primary`

---

## LL(1) 文法（建议版）

### 程序与语句

1. `Program -> StmtList EOF`
2. `StmtList -> Stmt StmtList | ε`
3. `Stmt -> ForStmt | Block | DeclStmt ';' | ';' | PrefixIncDec ';' | IDENT IdStmtTail ';'`
4. `Block -> '{' StmtList '}'`

> 说明：这里把“IDENT 起始语句”的冲突做了**因子分解**：
> - 若语句以 `IDENT` 开头，只需再看 1 个 lookahead（下一符号是 `IncDecOp` 还是 `AssignOp`）即可选择。
> - 项目代码里目前是直接在 `Stmt` 分支里用 `peek(1)` 做同等效果。

### for 语句

5. `ForStmt -> 'for' '(' ForInitOpt ';' ForCondOpt ';' ForIterOpt ')' Stmt`
6. `ForInitOpt -> DeclStmt | PrefixIncDec | IDENT ForIdTail | ε`
7. `ForCondOpt -> Expr | ε`
8. `ForIterOpt -> PrefixIncDec | IDENT ForIdTail | ε`

### 声明/赋值/自增自减

9.  `DeclStmt -> Type IDENT DeclInitOpt`
10. `Type -> 'int' | 'float' | 'double' | 'char'`
11. `DeclInitOpt -> '=' Expr | ε`

12. `AssignOp -> '=' | '+=' | '-=' | '*=' | '/='`

13. `IncDecOp -> '++' | '--'`
14. `PrefixIncDec -> IncDecOp IDENT`

15. `IdStmtTail -> IncDecOp | AssignOp Expr`
16. `ForIdTail -> IncDecOp | AssignOp Expr`

### 表达式（与代码实现一致的优先级）

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

## 关键 FIRST/SELECT 集合（用于代码里的 if/elif 分支）

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

### Stmt 的 SELECT（实现中用到的那一套）

- `SELECT(Stmt -> ForStmt) = { 'for' }`
- `SELECT(Stmt -> Block) = { '{' }`
- `SELECT(Stmt -> DeclStmt ';') = { 'int','float','double','char' }`
- `SELECT(Stmt -> ';') = { ';' }`
- `SELECT(Stmt -> PrefixIncDec ';') = { '++','--' }`
- `SELECT(Stmt -> IDENT IdStmtTail ';') = { 'IDENT' }`

---

## 与代码对应的位置

- 递归下降解析器：parser/rd_parser.py
  - SELECT/FIRST 集合常量：文件顶部 `_FIRST_EXPR` / `_SELECT_*`
  - for 的三段选择：`RDParser._for_stmt()`
  - 语句选择：`RDParser._stmt()`

