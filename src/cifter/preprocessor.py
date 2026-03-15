from __future__ import annotations

from dataclasses import dataclass

from pcpp import Preprocessor

from cifter.errors import CiftError


@dataclass
class _ConditionalFrame:
    parent_active: bool
    current_active: bool
    branch_taken: bool
    saw_else: bool = False


def preprocess_source(source: str, defines: list[str]) -> str:
    lines = source.splitlines()
    trailing_newline = source.endswith("\n")
    processor = Preprocessor()
    for define in defines:
        processor.define(_normalize_define(define))

    output: list[str] = []
    stack: list[_ConditionalFrame] = []

    for line in lines:
        directive = _parse_directive(line)
        active = stack[-1].current_active if stack else True

        if directive is not None and directive.name in {"if", "ifdef", "ifndef", "elif", "else", "endif"}:
            _handle_conditional_directive(processor, stack, directive)
            output.append("")
            continue

        if not active:
            output.append("")
            continue

        if directive is not None and directive.name == "define" and directive.body:
            processor.define(_normalize_define(directive.body))
        elif directive is not None and directive.name == "undef" and directive.body:
            processor.undef(directive.body.strip())

        output.append(line)

    if stack:
        raise CiftError("条件分岐ディレクティブが閉じていません")

    text = "\n".join(output)
    if trailing_newline:
        text += "\n"
    return text


@dataclass(frozen=True)
class _Directive:
    name: str
    body: str


def _parse_directive(line: str) -> _Directive | None:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return None
    body = stripped[1:].lstrip()
    if not body:
        return None
    name, _, tail = body.partition(" ")
    if not tail and "\t" in body:
        name, _, tail = body.partition("\t")
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
