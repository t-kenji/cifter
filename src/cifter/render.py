from __future__ import annotations

from cifter.model import ExtractionResult


def render_result(result: ExtractionResult) -> str:
    width = len(str(result.lines[-1].line_no))
    return "\n".join(f"{line.line_no:>{width}}: {line.text}" for line in result.lines)
