from __future__ import annotations

from dataclasses import replace

from cifter.model import ExtractedLine
from cifter.parser import SourceFile


def attach_omission_markers(
    source: SourceFile,
    lines: tuple[ExtractedLine, ...],
) -> tuple[ExtractedLine, ...]:
    if len(lines) < 2:
        return lines

    marked_lines: list[ExtractedLine] = []
    for index, line in enumerate(lines[:-1]):
        next_line = lines[index + 1]
        omitted_after_indent = None
        if next_line.line_no > line.line_no + 1:
            omitted_after_indent = omission_indent_for_gap(source, line.line_no + 1, next_line.line_no - 1, next_line)
        marked_lines.append(replace(line, omitted_after_indent=omitted_after_indent))
    marked_lines.append(lines[-1])
    return tuple(marked_lines)


def omission_indent_for_gap(
    source: SourceFile,
    start_line: int,
    end_line: int,
    next_line: ExtractedLine,
) -> str:
    for line_no in range(start_line, end_line + 1):
        line_text = source.line_text(line_no)
        if line_text.strip():
            return _leading_whitespace(line_text)
    return _leading_whitespace(next_line.text)


def _leading_whitespace(text: str) -> str:
    return text[: len(text) - len(text.lstrip())]
