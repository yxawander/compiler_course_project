from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from dfa.dfa import DFA
from dfa.dfa_state import DFAState
from dfa.dfa_minimizer import DFAMinimizer
from dfa.nfa_to_dfa_converter import NFAToDFAConverter
from nfa.nfa_builder import NFABuilder
from lexer.token import Token


@dataclass
class DFALexer:
    token_dfas: Dict[str, DFA] = field(default_factory=OrderedDict)
    patterns: "OrderedDict[str, str]" = field(default_factory=OrderedDict)

    def __post_init__(self) -> None:
        self._initialize_dfas()

    def _initialize_dfas(self) -> None:
        patterns: "OrderedDict[str, str]" = OrderedDict()

        # 关键字
        patterns["KEYWORD"] = "do|int|float|double|char|if|else|while|for|return|void|main"

        # 标识符
        patterns[
            "IDENTIFIER"
        ] = (
            "(a|b|c|d|e|f|g|h|i|j|k|l|m|n|o|p|q|r|s|t|u|v|w|x|y|z|A|B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z|_)"
            "(a|b|c|d|e|f|g|h|i|j|k|l|m|n|o|p|q|r|s|t|u|v|w|x|y|z|A|B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z|_|0|1|2|3|4|5|6|7|8|9)*"
        )

        # 整数
        patterns["INTEGER"] = "(1|2|3|4|5|6|7|8|9)(0|1|2|3|4|5|6|7|8|9)*|0"

        # 小数
        patterns[
            "FLOAT"
        ] = "(0|1|2|3|4|5|6|7|8|9)(0|1|2|3|4|5|6|7|8|9)*.(0|1|2|3|4|5|6|7|8|9)(0|1|2|3|4|5|6|7|8|9)*"

        # 运算符
        patterns[
            "OPERATOR"
        ] = (
            "==|!=|<=|>=|&&|\\|\\||\\+\\+|--|\\+=|-=|\\*=|/=|"
            "\\+|\\-|\\*|/|=|>|<|!"
        )

        # 分隔符
        patterns["DELIMITER"] = "\\(|\\)|\\{|\\}|\\[|\\]|;|,|:"

        # 保存一份，用于外部导出展示
        self.patterns = patterns

        nfa_builder = NFABuilder()

        for token_type, pattern in patterns.items():
            try:
                # 词法分析完整流程：正规式 -> NFA -> DFA -> 最小化DFA
                nfa = nfa_builder.build_nfa(pattern)
                dfa = NFAToDFAConverter(nfa).convert_to_dfa()
                minimized = DFAMinimizer().minimize(dfa)
                self.token_dfas[token_type] = minimized
            except Exception as e:
                print(f"❌ 构建 {token_type} 失败: {e}")

    def dump_patterns_and_dfas(self) -> str:
        lines: List[str] = []
        lines.append("========================================\n")
        lines.append("        正规式 / DFA 文本展示\n")
        lines.append("========================================\n\n")

        if not self.patterns:
            lines.append("(未找到 patterns，可能初始化失败或未设置)\n")
            return "".join(lines)

        for token_type, pattern in self.patterns.items():
            lines.append("----------------------------------------\n")
            lines.append(f"Token类型: {token_type}\n")
            lines.append(f"正规式(简化正则): {pattern}\n")

            dfa = self.token_dfas.get(token_type)
            if dfa is None:
                lines.append("DFA: (构建失败/不存在)\n")
                continue

            lines.append("\n")
            lines.append(str(dfa))
            lines.append("\n\n")

        return "".join(lines)

    def analyze(self, source_code: str) -> List[Token]:
        tokens: List[Token] = []
        position = 0
        line = 1
        column = 1

        while position < len(source_code):
            current_char = source_code[position]

            if current_char.isspace():
                if current_char == "\n":
                    line += 1
                    column = 1
                else:
                    column += 1
                position += 1
                continue

            token: Optional[Token]
            if current_char == '"':
                token = self._process_string_literal(source_code, position, line, column)
            else:
                token = self._find_longest_match(source_code, position, line, column)

            if token is not None:
                tokens.append(token)
                line, column = self._calculate_new_position(token.lexeme, line, column)
                position += len(token.lexeme)
            else:
                error_token = self._create_error_token(source_code, position, line, column)
                tokens.append(error_token)
                line, column = self._calculate_new_position(error_token.lexeme, line, column)
                position += len(error_token.lexeme)

        return tokens

    @staticmethod
    def _calculate_new_position(text: str, current_line: int, current_column: int) -> Tuple[int, int]:
        line = current_line
        column = current_column
        for c in text:
            if c == "\n":
                line += 1
                column = 1
            else:
                column += 1
        return line, column

    @staticmethod
    def _process_string_literal(source_code: str, position: int, line: int, column: int) -> Token:
        end = position + 1
        escaped = False
        while end < len(source_code):
            c = source_code[end]
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                end += 1
                break
            end += 1
        return Token("STRING", source_code[position:end], line, column)

    @staticmethod
    def _create_error_token(source_code: str, start: int, line: int, column: int) -> Token:
        end = start + 1
        while end < len(source_code):
            c = source_code[end]
            if c.isspace() or c in ";":
                break
            end += 1
        return Token("ERROR", source_code[start:end], line, column)

    def _find_longest_match(self, source_code: str, start: int, line: int, column: int) -> Optional[Token]:
        best_type: Optional[str] = None
        best_lexeme: Optional[str] = None
        max_length = 0

        for token_type, dfa in self.token_dfas.items():
            matched = self._run_dfa(dfa, source_code, start)
            if matched is not None and len(matched) > max_length:
                max_length = len(matched)
                best_type = token_type
                best_lexeme = matched

        if best_type is not None and best_lexeme is not None:
            return Token(best_type, best_lexeme, line, column)
        return None

    @staticmethod
    def _run_dfa(dfa: DFA, input_text: str, start: int) -> Optional[str]:
        current_state: DFAState = dfa.start_state
        matched_chars: List[str] = []
        position = start
        last_accepting: Optional[str] = None

        while position < len(input_text):
            c = input_text[position]
            next_state = current_state.get_transition(c)
            if next_state is None:
                break

            matched_chars.append(c)
            current_state = next_state
            if current_state.is_accepting:
                last_accepting = "".join(matched_chars)
            position += 1

        return last_accepting
