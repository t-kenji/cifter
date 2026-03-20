from __future__ import annotations

import sys
from io import StringIO
from typing import Protocol, TextIO

from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text

from cifter.model import (
    ExtractedLine,
    ExtractionItem,
    InlineHighlightSpan,
    RunResult,
)

TAB_SIZE = 4
TRACK_MATCH_STYLE = "bold on #3b82f6"


class _SupportsIsatty(Protocol):
    def isatty(self) -> bool:
        ...


def should_use_color(color: bool | None, file: TextIO | _SupportsIsatty) -> bool:
    if color is not None:
        return color
    isatty = getattr(file, "isatty", None)
    if not callable(isatty):
        return False
    return bool(isatty())


def render_result_text(run_result: RunResult) -> str:
    if not run_result.results:
        return ""
    if len(run_result.results) == 1:
        return _render_lines(run_result.results[0].lines)

    chunks: list[str] = []
    for item in run_result.results:
        chunks.append(_item_header(item))
        chunks.append(_render_lines(item.lines))
    return "\n\n".join(chunks)


def print_result_text(
    run_result: RunResult,
    *,
    color: bool | None,
    file: TextIO | None = None,
) -> None:
    output = file or sys.stdout
    if not should_use_color(color, output):
        rendered = render_result_text(run_result)
        if rendered:
            output.write(f"{rendered}\n")
        return

    if not run_result.results:
        return
    console = Console(file=StringIO(), record=True, force_terminal=True, color_system="truecolor")
    multiple = len(run_result.results) > 1
    for index, item in enumerate(run_result.results):
        if multiple:
            console.print(Text(_item_header(item), style="bold"))
        _print_item_lines(console, item)
        if multiple and index < len(run_result.results) - 1:
            console.print()
    output.write(console.export_text(styles=True))


def _render_lines(lines: tuple[ExtractedLine, ...]) -> str:
    width = len(str(lines[-1].line_no))
    rendered: list[str] = []
    for line in lines:
        rendered.append(f"{line.line_no:>{width}}: {line.text}")
        if line.omitted_after_indent is not None:
            rendered.append(f"{' ' * (width + 2)}{line.omitted_after_indent}...")
    return "\n".join(rendered)


def _item_header(item: ExtractionItem) -> str:
    header = (
        f"file: {item.file} "
        f"[{item.span.start_line}-{item.span.end_line}] "
        f"command={item.command} symbol={item.symbol}"
    )
    if item.routes:
        header += f" route={', '.join(item.routes)}"
    return header


def _print_item_lines(console: Console, item: ExtractionItem) -> None:
    syntax = Syntax("", item.language, tab_size=TAB_SIZE)
    width = len(str(item.lines[-1].line_no))
    for line in item.lines:
        prefix = f"{line.line_no:>{width}}: "
        highlighted_text = syntax.highlight(line.text)[:-1]
        rendered_line = Text.assemble((prefix, "dim"), highlighted_text)
        _apply_inline_highlights(rendered_line, line.text, line.highlights, column_offset=len(prefix))
        console.print(rendered_line)
        if line.omitted_after_indent is not None:
            console.print(Text(f"{' ' * (width + 2)}{line.omitted_after_indent}..."))


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
