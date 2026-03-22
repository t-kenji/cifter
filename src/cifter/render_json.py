from __future__ import annotations

import json

from cifter.model import ExtractionItem, ParseDiagnostic, RunDiagnostic, RunResult
from cifter.render_text import render_result_text


def render_result_json(run_result: RunResult) -> str:
    return json.dumps(
        {
            "tool_version": run_result.tool_version,
            "command": run_result.command,
            "inputs": [str(path) for path in run_result.inputs],
            "results": [_serialize_item(item) for item in run_result.results],
            "diagnostics": [_serialize_run_diagnostic(item) for item in run_result.diagnostics],
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _serialize_item(item: ExtractionItem) -> dict[str, object]:
    return {
        "file": str(item.file),
        "symbol": item.symbol,
        "kind": item.kind,
        "span": {
            "file": str(item.span.file),
            "start_line": item.span.start_line,
            "end_line": item.span.end_line,
        },
        "language": item.language,
        "rendered_lines": [
            {
                "line_no": line.line_no,
                "text": line.text,
                "omitted_after_indent": line.omitted_after_indent,
                "highlights": [
                    {
                        "start_column": highlight.start_column,
                        "end_column": highlight.end_column,
                        "kind": highlight.kind,
                    }
                    for highlight in line.highlights
                ],
            }
            for line in item.lines
        ],
        "rendered_text": render_result_text(
            RunResult(
                tool_version="",
                command=item.kind,
                inputs=(),
                results=(item,),
                diagnostics=(),
            )
        ),
        "diagnostics": [_serialize_parse_diagnostic(diagnostic) for diagnostic in item.diagnostics],
        "routes": list(item.routes),
    }


def _serialize_parse_diagnostic(diagnostic: ParseDiagnostic) -> dict[str, object]:
    return {
        "category": diagnostic.category,
        "code": diagnostic.code,
        "message": diagnostic.message,
        "details": dict(diagnostic.details),
    }


def _serialize_run_diagnostic(diagnostic: RunDiagnostic) -> dict[str, object]:
    return {
        "severity": diagnostic.severity,
        "code": diagnostic.code,
        "message": diagnostic.message,
        "file": str(diagnostic.file) if diagnostic.file is not None else None,
    }
