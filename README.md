# compiler_course_project

编译原理课设（for循环语句翻译--递归下降法、输出三地址码）

## 运行

在项目根目录执行：

- `python main.py test1.txt`
- `python main.py test2.txt`

程序会在同目录自动生成：

- `*_正规式与DFA.txt`（单词正规式 + DFA 文本转移表）
- `*_词法分析结果.txt`（词法分析过程 + 二元式/Token 输出 + 词法错误提示）
- `*_递归下降日志.txt`（语法分析过程 + 语义/中间代码生成过程 + 报错）
- `*_三地址码与四元式.txt`
- `*_FIRST_FOLLOW_SELECT.txt`（分析表相关集合，自动生成）

## 报错测试用例

- `test3_lex_error.txt`：包含非法字符 `@`，会触发词法错误 Token；递归下降阶段会跳过错误 Token 继续分析。
- `test4_syn_error.txt`：故意缺少分号 `;`，会触发语法错误（含行列、得到/期望）。
- `test5_sem_error.txt`：语义错误示例（类型不兼容、使用未声明变量、块级作用域遮蔽），会在递归下降日志中输出“语义错误”。
