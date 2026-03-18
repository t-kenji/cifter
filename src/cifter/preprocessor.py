from __future__ import annotations

from dataclasses import dataclass

from pcpp import Preprocessor

from cifter.errors import CiftError
from cifter.model import ParseDiagnostic

CONDITIONAL_DIRECTIVES = {"if", "ifdef", "ifndef", "elif", "else", "endif"}
SUPPORTED_DIRECTIVES = CONDITIONAL_DIRECTIVES | {"define", "undef", "include", "pragma", "error"}


@dataclass
class _ConditionalFrame:
    parent_active: bool
    current_active: bool
    branch_taken: bool
    saw_else: bool = False


@dataclass(frozen=True)
class PreprocessResult:
    text: str
    diagnostics: tuple[ParseDiagnostic, ...]


@dataclass(frozen=True)
class _Directive:
    name: str
    body: str


@dataclass(frozen=True)
class _LogicalLine:
    text: str
    physical_lines: tuple[str, ...]
    start_line: int


def preprocess_source(source: str, defines: list[str]) -> PreprocessResult:
    lines = tuple(source.splitlines())
    trailing_newline = source.endswith("\n")
    processor = Preprocessor()
    for define in defines:
        processor.define(_normalize_define(define))

    output: list[str] = []
    stack: list[_ConditionalFrame] = []
    diagnostics: list[ParseDiagnostic] = []

    for logical_line in _iter_logical_lines(lines):
        directive = _parse_directive(logical_line.text)
        active = stack[-1].current_active if stack else True

        if directive is not None and directive.name in CONDITIONAL_DIRECTIVES:
            _handle_conditional_directive(processor, stack, directive)
            output.extend("" for _ in logical_line.physical_lines)
            continue

        if not active:
            output.extend("" for _ in logical_line.physical_lines)
            continue

        if directive is not None and directive.name == "define" and directive.body:
            processor.define(directive.body)
        elif directive is not None and directive.name == "undef" and directive.body:
            processor.undef(directive.body.strip())
        elif directive is not None and directive.name not in SUPPORTED_DIRECTIVES:
            diagnostics.append(
                ParseDiagnostic(
                    category="preprocess",
                    code="unsupported_directive",
                    message=f"未対応ディレクティブ #{directive.name} を保持したまま解析しました",
                    details=(
                        ("directive", directive.name),
                        ("line", str(logical_line.start_line)),
                    ),
                )
            )

        output.extend(logical_line.physical_lines)

    if stack:
        raise CiftError("条件分岐ディレクティブが閉じていません")

    text = "\n".join(output)
    if trailing_newline:
        text += "\n"
    return PreprocessResult(text=text, diagnostics=tuple(diagnostics))


def _iter_logical_lines(lines: tuple[str, ...]) -> tuple[_LogicalLine, ...]:
    logical_lines: list[_LogicalLine] = []
    index = 0
    while index < len(lines):
        start_line = index + 1
        physical_lines = [lines[index]]
        logical_text = lines[index]
        while logical_text.endswith("\\") and index + 1 < len(lines):
            logical_text = logical_text[:-1] + lines[index + 1]
            index += 1
            physical_lines.append(lines[index])
        logical_lines.append(
            _LogicalLine(
                text=logical_text,
                physical_lines=tuple(physical_lines),
                start_line=start_line,
            )
        )
        index += 1
    return tuple(logical_lines)


def _parse_directive(line: str) -> _Directive | None:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return None
    body = stripped[1:].lstrip()
    if not body:
        return None
    parts = body.split(None, 1)
    name = parts[0]
    tail = parts[1] if len(parts) > 1 else ""
    return _Directive(name=name, body=tail.lstrip())


def _handle_conditional_directive(
    processor: Preprocessor,
    stack: list[_ConditionalFrame],
    directive: _Directive,
) -> None:
    name = directive.name
    if name in {"if", "ifdef", "ifndef"}:
        parent_active = stack[-1].current_active if stack else True
        current_active = parent_active and _evaluate_condition(processor, directive)
        stack.append(
            _ConditionalFrame(
                parent_active=parent_active,
                current_active=current_active,
                branch_taken=current_active,
            )
        )
        return

    if not stack:
        raise CiftError(f"対応する開始ディレクティブがありません: #{name}")

    frame = stack[-1]
    if name == "elif":
        if frame.saw_else:
            raise CiftError("#else の後に #elif は指定できません")
        if frame.branch_taken:
            frame.current_active = False
            return
        frame.current_active = frame.parent_active and _evaluate_condition(processor, directive)
        frame.branch_taken = frame.current_active
        return
    if name == "else":
        if frame.saw_else:
            raise CiftError("#else は 1 回だけ指定できます")
        frame.saw_else = True
        frame.current_active = frame.parent_active and not frame.branch_taken
        frame.branch_taken = True
        return
    if name == "endif":
        stack.pop()
        return


def _evaluate_condition(processor: Preprocessor, directive: _Directive) -> bool:
    if directive.name == "ifdef":
        return directive.body.strip() in processor.macros
    if directive.name == "ifndef":
        return directive.body.strip() not in processor.macros
    value, _ = processor.evalexpr(processor.tokenize(directive.body))
    return bool(value)


def _normalize_define(value: str) -> str:
    name, separator, body = value.partition("=")
    if not separator:
        return value
    return f"{name.strip()} {body.strip()}"
