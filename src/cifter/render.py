from __future__ import annotations

import sys
from io import StringIO
from typing import Protocol, TextIO

from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text

from cifter.model import ExtractionResult, InlineHighlightSpan

TAB_SIZE = 4
TRACK_MATCH_STYLE = "bold on #3b82f6"


class _SupportsIsatty(Protocol):
    def isatty(self) -> bool:
        ...


def render_result(result: ExtractionResult) -> str:
    width = len(str(result.lines[-1].line_no))
    return "\n".join(f"{line.line_no:>{width}}: {line.text}" for line in result.lines)


def print_result(
    result: ExtractionResult,
    language_name: str,
    *,
    color: bool | None,
    file: TextIO | None = None,
) -> None:
    output = file or sys.stdout
    if not _should_use_color(color, output):
        output.write(f"{render_result(result)}\n")
        return

    console = Console(
        file=StringIO(),
        record=True,
        force_terminal=True,
        color_system="truecolor",
    )
    syntax = Syntax("", language_name, tab_size=TAB_SIZE)
    width = len(str(result.lines[-1].line_no))
    for line in result.lines:
        prefix = f"{line.line_no:>{width}}: "
        highlighted_text = syntax.highlight(line.text)[:-1]
        rendered_line = Text.assemble(
            (prefix, "dim"),
            highlighted_text,
        )
        _apply_inline_highlights(rendered_line, line.text, line.highlights, column_offset=len(prefix))
        console.print(rendered_line)
    output.write(console.export_text(styles=True))


def _should_use_color(color: bool | None, file: TextIO | _SupportsIsatty) -> bool:
    if color is not None:
        return color
    isatty = getattr(file, "isatty", None)
    if not callable(isatty):
        return False
    return bool(isatty())


def _apply_inline_highlights(
    text: Text,
    source_text: str,
    highlights: tuple[InlineHighlightSpan, ...],
    *,
    column_offset: int = 0,
) -> None:
    text_length = len(text.plain)
    for highlight in highlights:
        if highlight.kind != "track_match":
            continue
        start = column_offset + _rendered_column_for_source_column(source_text, highlight.start_column)
        end = column_offset + _rendered_column_for_source_column(source_text, highlight.end_column)
        start = max(0, min(start, text_length))
        end = max(start, min(end, text_length))
        if start == end:
            continue
        text.stylize(TRACK_MATCH_STYLE, start, end)


def _rendered_column_for_source_column(source_text: str, source_column: int) -> int:
    rendered_column = 0
    for char in source_text[: max(0, min(source_column, len(source_text)))]:
        if char == "\t":
            rendered_column += TAB_SIZE - (rendered_column % TAB_SIZE)
            continue
        rendered_column += 1
    return rendered_column
