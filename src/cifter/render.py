from __future__ import annotations

import sys
from io import StringIO
from typing import TextIO

from rich.console import Console
from rich.syntax import Syntax
from rich.text import Text

from cifter.model import ExtractionResult


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
    syntax = Syntax("", language_name)
    width = len(str(result.lines[-1].line_no))
    for line in result.lines:
        rendered_line = Text.assemble(
            (f"{line.line_no:>{width}}: ", "dim"),
            syntax.highlight(line.text)[:-1],
        )
        console.print(rendered_line)
    output.write(console.export_text(styles=True))


def _should_use_color(color: bool | None, file: TextIO) -> bool:
    if color is not None:
        return color
    isatty = getattr(file, "isatty", None)
    if not callable(isatty):
        return False
    return bool(isatty())
