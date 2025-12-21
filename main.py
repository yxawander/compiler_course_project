from __future__ import annotations

import locale
import sys
import time
from pathlib import Path
from typing import List, Optional

_THIS_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _THIS_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from lexer.dfa_lexer import DFALexer
from lexer.token import Token
from parser.rd_parser import RDParser
from parser.stream import TokenStream, normalize_tokens


def prompt_for_file_path() -> str:
    return input("请输入源文件路径（相对项目根目录或绝对路径均可）:\n> ").strip()


def resolve_file_path(file_path: str) -> Optional[Path]:
    try:
        if not file_path:
            return None

        # 处理带引号的路径（Windows 常见）
        if file_path.startswith('"') and file_path.endswith('"') and len(file_path) >= 2:
            file_path = file_path[1:-1]

        path = Path(file_path).expanduser()

        # 如果是绝对路径，直接返回
        if path.is_absolute():
            return path

        # 相对路径：按这些基准目录依次尝试
        candidates = [
            _ROOT_DIR / path,   # 项目根目录（优先）
            _THIS_DIR / path,   # 当前 main.py 所在目录
            Path.cwd() / path,  # 当前工作目录（运行时）
            Path.home() / path, # 用户目录
        ]

        for p in candidates:
            if p.exists():
                return p

        # 都不存在时：仍返回“相对项目根目录”的拼接结果，便于后续报错信息更直观
        return _ROOT_DIR / path
    except Exception:
        return None


def detect_file_encoding(path: Path) -> Optional[str]:
    try:
        data = path.open("rb").read(4)
        if len(data) >= 3 and data[0:3] == b"\xEF\xBB\xBF":
            return "utf-8-sig"
        if len(data) >= 2 and data[0:2] == b"\xFE\xFF":
            return "utf-16-be"
        if len(data) >= 2 and data[0:2] == b"\xFF\xFE":
            return "utf-16-le"
        if len(data) >= 4 and data[0:4] == b"\x00\x00\xFE\xFF":
            return "utf-32-be"
        if len(data) >= 4 and data[0:4] == b"\xFF\xFE\x00\x00":
            return "utf-32-le"
    except Exception:
        pass
    return None


def read_source_file(path: Path) -> Optional[str]:
    encoding = detect_file_encoding(path)
    print(f"检测到文件编码: {encoding if encoding is not None else 'UTF-8 (默认)'}")

    try:
        if encoding is None:
            encoding = locale.getpreferredencoding(False) or "utf-8"

        with path.open("r", encoding=encoding) as f:
            lines = f.readlines()

        print(f"读取行数: {len(lines)}")
        content = "".join(lines)
        if content.endswith("\n"):
            content = content[:-1]
        return content
    except FileNotFoundError:
        print(f"文件未找到: {path}")
    except Exception as e:
        print(f"读取文件错误: {e}")
    return None


def get_output_file_path(source_file: Path) -> Path:
    base = source_file.stem
    return source_file.with_name(f"{base}_lexer_output.txt")


def get_regex_dfa_output_file_path(source_file: Path) -> Path:
    base = source_file.stem
    return source_file.with_name(f"{base}_regex_dfa.txt")

def get_tac_output_file_path(source_file: Path) -> Path:
    base = source_file.stem
    return source_file.with_name(f"{base}_tac_output.txt")


def get_rd_parser_log_file_path(source_file: Path) -> Path:
    base = source_file.stem
    return source_file.with_name(f"{base}_rd_parser_log.txt")


def format_lexeme_for_display(lexeme: Optional[str]) -> str:
    if not lexeme:
        return "[空]"

    out: List[str] = []
    for c in lexeme:
        if c == "\n":
            out.append("\\n")
        elif c == "\t":
            out.append("\\t")
        elif c == "\r":
            out.append("\\r")
        elif c == "\b":
            out.append("\\b")
        elif c == "\f":
            out.append("\\f")
        elif c == '"':
            out.append('\\"')
        elif c == "'":
            out.append("\\'")
        elif c == "\\":
            out.append("\\\\")
        else:
            code = ord(c)
            if code < 32 or code > 126:
                out.append(f"\\u{code:04x}")
            else:
                out.append(c)

    formatted = "".join(out)
    if len(formatted) > 50:
        return formatted[:47] + "..."
    return formatted


def print_and_save_results(tokens: List[Token], output_file_path: Path, source_file_name: str) -> None:
    title = (
        "========================================\n"
        "          词法分析结果报告\n"
        "========================================\n"
        f"源文件: {source_file_name}\n"
        "========================================\n\n"
    )

    console_output: List[str] = [title]
    file_output: List[str] = [title]

    token_count = 0
    error_count = 0
    keyword_count = 0
    identifier_count = 0
    integer_count = 0
    float_count = 0
    operator_count = 0
    delimiter_count = 0
    string_count = 0

    current_line = -1

    for token in tokens:
        token_count += 1

        if token.line != current_line:
            if current_line != -1:
                sep = "────────────────────────────────────────\n"
                console_output.append(sep)
                file_output.append(sep)
            current_line = token.line

        if token.type == "KEYWORD":
            keyword_count += 1
        elif token.type == "IDENTIFIER":
            identifier_count += 1
        elif token.type == "INTEGER":
            integer_count += 1
        elif token.type == "FLOAT":
            float_count += 1
        elif token.type == "OPERATOR":
            operator_count += 1
        elif token.type == "DELIMITER":
            delimiter_count += 1
        elif token.type == "STRING":
            string_count += 1
        elif token.type == "ERROR":
            error_count += 1

        line_str = f"行{token.line:4d}, 列{token.column:3d} | {token.type:<15s} | {format_lexeme_for_display(token.lexeme)}\n"
        console_output.append(line_str)
        file_output.append(line_str)

        if token.type == "ERROR":
            err = f"           ⚠ 错误: 无法识别的符号 '{token.lexeme}'\n"
            console_output.append(err)
            file_output.append(err)

    if current_line != -1:
        sep = "────────────────────────────────────────\n"
        console_output.append(sep)
        file_output.append(sep)

    stats = (
        "\n========================================\n"
        "             统计信息\n"
        "========================================\n"
        f"总Token数:     {token_count:8d}\n"
        "────────────────────────────────────────\n"
        f"关键字:        {keyword_count:8d}\n"
        f"标识符:        {identifier_count:8d}\n"
        f"整数:          {integer_count:8d}\n"
        f"小数:          {float_count:8d}\n"
        f"运算符:        {operator_count:8d}\n"
        f"分隔符:        {delimiter_count:8d}\n"
        f"字符串:        {string_count:8d}\n"
        "────────────────────────────────────────\n"
        f"错误Token:     {error_count:8d}\n"
        f"错误率:        {(error_count * 100.0 / token_count) if token_count else 0.0:8.2f}%\n"
        "========================================\n"
        "分析完成。\n"
    )

    console_output.append(stats)
    file_output.append(stats)

    print("".join(console_output), end="")

    try:
        output_file_path.write_text("".join(file_output), encoding="utf-8")
        print(f"\n结果已保存到: {output_file_path.resolve()}")
        print(f"文件大小: {output_file_path.stat().st_size} 字节")
    except Exception as e:
        print(f"保存输出文件错误: {e}")
        print("尝试保存到备用位置...")
        try:
            backup = Path(f"lexer_output_{int(time.time() * 1000)}.txt")
            backup.write_text("".join(file_output), encoding="utf-8")
            print(f"结果已保存到备用位置: {backup}")
        except Exception as ex:
            print(f"备用保存也失败: {ex}")
            print("控制台输出已保留，请手动复制保存。")


def main(argv: List[str]) -> int:
    if len(argv) >= 2:
        source_file_path = argv[1]
    else:
        source_file_path = prompt_for_file_path()
        if not source_file_path:
            print("未提供源文件路径，程序退出。")
            return 1

    source_file = resolve_file_path(source_file_path)
    if source_file is None:
        print(f"错误: 无法解析文件路径 - {source_file_path}")
        return 1

    if not source_file.exists():
        print(f"错误: 源文件不存在 - {source_file.resolve()}")
        return 1

    if not source_file.is_file():
        print(f"错误: 路径不是文件 - {source_file.resolve()}")
        return 1

    try:
        with source_file.open("rb"):
            pass
    except Exception:
        print(f"错误: 无法读取文件 - {source_file.resolve()}")
        return 1

    print(f"正在分析文件: {source_file.resolve()}")

    source_code = read_source_file(source_file)
    if source_code is None:
        print("错误: 无法读取源文件内容")
        return 1

    print(f"文件读取成功，大小: {len(source_code)} 字符")

    lexer = DFALexer()

    # 输出“正规式 + DFA(文本转移表)”到同目录 txt
    try:
        regex_dfa_path = get_regex_dfa_output_file_path(source_file)
        regex_dfa_path.write_text(lexer.dump_patterns_and_dfas(), encoding="utf-8")
        print(f"正规式/DFA文本已保存到: {regex_dfa_path.resolve()}")
    except Exception as e:
        print(f"保存正规式/DFA文本失败: {e}")

    print("开始词法分析...")
    start = time.time()
    tokens = lexer.analyze(source_code)
    end = time.time()
    print(f"词法分析完成，耗时: {int((end - start) * 1000)}ms")

    output_file_path = get_output_file_path(source_file)
    print_and_save_results(tokens, output_file_path, source_file.name)

    # 递归下降语法分析 + 三地址码生成（for 循环翻译）
    print("\n开始递归下降语法分析与三地址码生成...")
    lex_error_count = sum(1 for t in tokens if t.type == "ERROR")
    if lex_error_count:
        print(f"⚠ 检测到 {lex_error_count} 个词法错误Token，递归下降阶段将跳过这些Token继续进行。")

    syntax_tokens = normalize_tokens(tokens, drop_error_tokens=True)
    parser = RDParser(TokenStream(syntax_tokens))
    start2 = time.time()
    result = parser.parse_program()
    end2 = time.time()
    print(f"递归下降/中间代码阶段完成，耗时: {int((end2 - start2) * 1000)}ms")

    rd_log_path = get_rd_parser_log_file_path(source_file)
    try:
        rd_log_text = []
        rd_log_text.append("========================================\n")
        rd_log_text.append("        递归下降解析日志\n")
        rd_log_text.append("========================================\n\n")
        rd_log_text.append("\n".join(result.parse_trace))
        rd_log_text.append("\n\n")
        rd_log_text.append("========================================\n")
        rd_log_text.append("      语义/中间代码生成日志\n")
        rd_log_text.append("========================================\n\n")
        rd_log_text.append("\n".join(result.sem_trace))
        if result.errors:
            rd_log_text.append("\n\n")
            rd_log_text.append("========================================\n")
            rd_log_text.append("            语法错误\n")
            rd_log_text.append("========================================\n\n")
            rd_log_text.append("\n".join(str(e) for e in result.errors))
        rd_log_path.write_text("".join(rd_log_text), encoding="utf-8")
        print(f"递归下降日志已保存到: {rd_log_path.resolve()}")
    except Exception as e:
        print(f"保存递归下降日志失败: {e}")

    tac_report_path = get_tac_output_file_path(source_file)
    try:
        tac_report_path.write_text(
            result.emitter.as_text() + "\n\n" + result.emitter.as_quads_text(),
            encoding="utf-8",
        )
        print(f"三地址码/四元式已保存到: {tac_report_path.resolve()}")
    except Exception as e:
        print(f"保存三地址码/四元式失败: {e}")

    if result.errors:
        print(f"⚠ 语法错误数: {len(result.errors)}（请根据控制台报错定位）")
    else:
        print("语法分析通过：未发现语法错误。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
