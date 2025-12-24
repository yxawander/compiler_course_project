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

  ---

  ## 属性文法 / 语法制导定义（SDD / SDT，与本项目四元式生成一致）

  > 这一节把“语义动作”从代码里抽出来，用属性文法（更准确地说是 SDD/SDT）的写法描述。
  > 本项目中表达式/语句的核心语义就是：
  > - 计算表达式结果保存到一个“地址/临时变量”里（`place`）
  > - 产生四元式（或三地址码）到 `emitter`

  ### 约定

  **符号属性**

  - 对表达式相关非终结符：
    - `X.place`：综合属性（synthesized），表示该子表达式计算结果所在的位置（变量名或临时变量名）。
  - 对尾部递归非终结符（`RelTail / AddTail / MulTail`）：
    - `Tail.in`：继承属性（inherited），表示“到目前为止已计算出的左值 place”。
    - `Tail.place`：综合属性，表示该 Tail 链完成后最终的 place。

  **语义例程（与代码同名/同含义）**

  - `newtemp()`：生成临时变量（对应 `TACEmitter.new_temp()`）
  - `newlabel()`：生成标签（对应 `TACEmitter.new_label()`）
  - `emit(op, a1, a2, res)`：输出四元式（对应 `TACEmitter.emit()`）
  - `emit_label(L)`：输出标签（对应 `emit("label", result=L)`）
  - `emit_goto(L)`：无条件跳转（对应 `emit("goto", result=L)`）
  - `emit_ifFalse_placeholder(cond_place)`：生成“ifFalse cond goto ?”并返回待回填位置（对应 `emit_if_false_placeholder`）
  - `backpatch(list, L)`：把 list 里的跳转目标回填为 L（对应 `backpatch`）

  > 说明：你的 `for` 在解析括号内部时用 `_DeferredEmitter` 做了“先缓冲、后 flush”的技巧。
  > 属性文法这里不描述缓冲细节，只描述**最终中间代码的执行顺序**，与输出结果一致。

  ---

  ### 声明语句

  1) `DeclStmt -> Type IDENT DeclInitOpt`

  - 若 `DeclInitOpt` 选择 `'= Expr'`：
    - `emit('=', Expr.place, '', IDENT.lexeme)`
  - 若 `DeclInitOpt` 选择 `ε`：无语义动作

  2) `DeclInitOpt -> '=' Expr | ε`

  ---

  ### 赋值语句 / 自增自减语句

  为了 LL(1)（并与当前实现一致），把 `IDENT` 起始语句因子分解为：

  3) `Stmt -> IDENT IdStmtTail ';'`

  4) `IdStmtTail -> IncDecOp`

  - 设语句开头的标识符为 `id`（来自 `Stmt` 里的 `IDENT`）：
    - `t = newtemp()`
    - 若 `IncDecOp` 为 `'++'`：`emit('+', id, '1', t)`
    - 若 `IncDecOp` 为 `'--'`：`emit('-', id, '1', t)`
    - `emit('=', t, '', id)`

  5) `IdStmtTail -> AssignOp Expr`

  - 设语句开头的标识符为 `id`：
    - 若 `AssignOp` 为 `'='`：
      - `emit('=', Expr.place, '', id)`
    - 若 `AssignOp` 为 `'+=' | '-=' | '*=' | '/='`：
      - `t = newtemp()`
      - 令 `op` 分别映射为 `'+' | '-' | '*' | '/'`
      - `emit(op, id, Expr.place, t)`
      - `emit('=', t, '', id)`

  6) `PrefixIncDec -> IncDecOp IDENT`（语句起始为 `++/--` 的情况）

  - 与上面 Inc/Dec 相同，只是 `id` 来自右侧的 `IDENT`。

  7) `AssignOp -> '=' | '+=' | '-=' | '*=' | '/='`（无属性/无动作）
  8) `IncDecOp -> '++' | '--'`（无属性/无动作）

  ---

  ### for 语句（控制流 + 回填）

  文法：

  `ForStmt -> 'for' '(' ForInitOpt ';' ForCondOpt ';' ForIterOpt ')' Stmt`

  语义（与最终输出的四元式顺序一致）：

  1) 先执行初始化部分（仅一次）：`ForInitOpt` 的语义动作
  2) `L_begin = newlabel(); emit_label(L_begin)`
  3) 每轮循环的条件判断：
     - 若 `ForCondOpt -> Expr`：
       - 先执行 `Expr` 的四元式（计算出 `ForCondOpt.place = Expr.place`）
       - `p = emit_ifFalse_placeholder(ForCondOpt.place)`
     - 若 `ForCondOpt -> ε`：不生成 ifFalse（等价于条件恒真）
  4) 执行循环体：`Stmt` 的语义动作
  5) 执行迭代部分（每轮一次）：`ForIterOpt` 的语义动作
  6) `emit_goto(L_begin)`
  7) `L_end = newlabel(); emit_label(L_end)`
  8) 若存在 `p`：`backpatch([p], L_end)`

  `ForInitOpt / ForIterOpt` 的三类语义：

  - 若为 `DeclStmt`：按“声明语句”的语义生成
  - 若为 `PrefixIncDec` 或 `IDENT ForIdTail`：按“自增自减/赋值语句”的语义生成
  - 若为 `ε`：无动作

  `ForIdTail` 与 `IdStmtTail` 完全同构，语义相同（只是出现在 for 的括号里）。

  ---

  ### 表达式（place 综合属性 + 运算四元式）

  表达式优先级与你代码一致：Rel > Add > Mul > Unary > Primary。

  **关系表达式（允许链式 relop）**

  1) `Expr -> AddExpr RelTail`

  - `RelTail.in = AddExpr.place`
  - `Expr.place = RelTail.place`

  2) `RelTail -> RelOp AddExpr RelTail1`

  - `t = newtemp()`
  - `emit(RelOp.op, RelTail.in, AddExpr.place, t)`
  - `RelTail1.in = t`
  - `RelTail.place = RelTail1.place`

  3) `RelTail -> ε`

  - `RelTail.place = RelTail.in`

  **加法链**

  4) `AddExpr -> MulExpr AddTail`

  - `AddTail.in = MulExpr.place`
  - `AddExpr.place = AddTail.place`

  5) `AddTail -> AddOp MulExpr AddTail1`

  - `t = newtemp()`
  - `emit(AddOp.op, AddTail.in, MulExpr.place, t)`
  - `AddTail1.in = t`
  - `AddTail.place = AddTail1.place`

  6) `AddTail -> ε`

  - `AddTail.place = AddTail.in`

  **乘法链**

  7) `MulExpr -> Unary MulTail`

  - `MulTail.in = Unary.place`
  - `MulExpr.place = MulTail.place`

  8) `MulTail -> MulOp Unary MulTail1`

  - `t = newtemp()`
  - `emit(MulOp.op, MulTail.in, Unary.place, t)`
  - `MulTail1.in = t`
  - `MulTail.place = MulTail1.place`

  9) `MulTail -> ε`

  - `MulTail.place = MulTail.in`

  **一元表达式**

  10) `Unary -> UnaryOp Unary1`

  - 若 `UnaryOp` 为 `'+'`：`Unary.place = Unary1.place`
  - 若 `UnaryOp` 为 `'-'`：
    - `t = newtemp()`
    - `emit('-', '0', Unary1.place, t)`
    - `Unary.place = t`
  - 若 `UnaryOp` 为 `'!'`：
    - `t = newtemp()`
    - `emit('!', Unary1.place, '', t)`
    - `Unary.place = t`

  11) `Unary -> Primary`

  - `Unary.place = Primary.place`

  **基本项**

  12) `Primary -> IDENT`

  - `Primary.place = IDENT.lexeme`

  13) `Primary -> NUM`

  - `Primary.place = NUM.lexeme`

  14) `Primary -> '(' Expr ')'`

  - `Primary.place = Expr.place`

  ---

  ### 空语句 / 块

  - `Stmt -> ';'`：无动作
  - `Block -> '{' StmtList '}'`：无动作（仅包含内部语句的动作）

  ---

  ### 与代码对应的位置（语义部分）

  - 表达式 place 返回值：`RDParser._expr/_add_expr/_mul_expr/_unary/_primary`
  - 四元式输出：`self.emitter.emit(...)`，临时变量：`self.emitter.new_temp()`
  - for 的控制流：`RDParser._for_stmt()`（`label/goto/ifFalse/backpatch`）

  - 语句选择：`RDParser._stmt()`

