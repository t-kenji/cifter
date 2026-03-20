from __future__ import annotations

from tree_sitter import Node

from cifter.model import ExtractedLine, ExtractionResult
from cifter.parser import ParsedSource, find_function


def extract_function(parsed: ParsedSource, name: str) -> ExtractionResult:
    return extract_function_node(parsed, find_function(parsed, name))


def extract_function_node(parsed: ParsedSource, function_node: Node) -> ExtractionResult:
    start_line = function_node.start_point.row + 1
    end_line = function_node.end_point.row + 1
    lines = tuple(
        ExtractedLine(line_no=line_no, text=parsed.source.line_text(line_no))
        for line_no in range(start_line, end_line + 1)
    )
    return ExtractionResult(span=parsed.source.span_for_lines(list(range(start_line, end_line + 1))), lines=lines)
