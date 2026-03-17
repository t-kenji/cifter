from __future__ import annotations

from tree_sitter import Node

from cifter.model import ExtractedLine, ExtractionResult, InlineHighlightSpan, TrackPath
from cifter.parser import ParsedSource, find_function, function_body, node_text

CONTROL_TYPES = {
    "if_statement",
    "switch_statement",
    "case_statement",
    "for_statement",
    "while_statement",
    "do_statement",
    "goto_statement",
    "break_statement",
    "continue_statement",
    "return_statement",
    "labeled_statement",
}

STATEMENT_TYPES = {
    "expression_statement",
    "declaration",
    "goto_statement",
    "break_statement",
    "continue_statement",
    "return_statement",
}
def extract_flow(
    parsed: ParsedSource,
    function_name: str,
    tracks: tuple[TrackPath, ...],
    *,
    include_highlights: bool = False,
) -> ExtractionResult:
    function_node = find_function(parsed, function_name)
    body = function_body(function_node)
    keep: set[int] = set()
    highlights: dict[int, set[InlineHighlightSpan]] = {}
    _keep_range(keep, function_node.start_point.row + 1, body.start_point.row + 1)
    keep.add(body.end_point.row + 1)
    _collect_from_container(parsed, body, keep, highlights, tracks, include_highlights)
    line_numbers = sorted(keep)
    lines = tuple(
        ExtractedLine(
            line_no=line_no,
            text=parsed.source.line_text(line_no),
            highlights=tuple(
                sorted(
                    highlights.get(line_no, ()),
                    key=lambda highlight: (highlight.start_column, highlight.end_column, highlight.kind),
                )
            ),
        )
        for line_no in line_numbers
    )
    return ExtractionResult(span=parsed.source.span_for_lines(line_numbers), lines=lines)


def _collect_from_container(
    parsed: ParsedSource,
    container: Node,
    keep: set[int],
    highlights: dict[int, set[InlineHighlightSpan]],
    tracks: tuple[TrackPath, ...],
    include_highlights: bool,
) -> None:
    for statement in _container_statements(container):
        _collect_statement(parsed, statement, keep, highlights, tracks, include_highlights)


def _collect_statement(
    parsed: ParsedSource,
    statement: Node,
    keep: set[int],
    highlights: dict[int, set[InlineHighlightSpan]],
    tracks: tuple[TrackPath, ...],
    include_highlights: bool,
) -> None:
    track_matches = _collect_track_matches(parsed, statement, tracks)
    if include_highlights:
        _record_track_highlights(parsed, track_matches, highlights)
    if statement.type == "switch_statement":
        body = statement.named_children[-1]
        _keep_range(keep, statement.start_point.row + 1, body.start_point.row + 1)
        keep.add(body.end_point.row + 1)
        _collect_from_container(parsed, body, keep, highlights, tracks, include_highlights)
        return
    if statement.type == "case_statement":
        keep.add(statement.start_point.row + 1)
        body = _case_body_container(statement)
        if body is not statement:
            _keep_range(keep, body.start_point.row + 1, body.start_point.row + 1)
            keep.add(body.end_point.row + 1)
        _collect_from_container(parsed, body, keep, highlights, tracks, include_highlights)
        return
    if statement.type == "if_statement":
        _collect_if_chain(parsed, statement, keep, highlights, tracks, include_highlights)
        return
    if statement.type in {"for_statement", "while_statement"}:
        body = statement.named_children[-1]
        _keep_range(keep, statement.start_point.row + 1, body.start_point.row + 1)
        if body.type == "compound_statement":
            keep.add(body.end_point.row + 1)
            _collect_from_container(parsed, body, keep, highlights, tracks, include_highlights)
        else:
            _collect_statement(parsed, body, keep, highlights, tracks, include_highlights)
        return
    if statement.type == "do_statement":
        body = statement.named_children[0]
        keep.add(statement.start_point.row + 1)
        keep.add(statement.end_point.row + 1)
        if body.type == "compound_statement":
            keep.add(body.end_point.row + 1)
            _collect_from_container(parsed, body, keep, highlights, tracks, include_highlights)
        else:
            _collect_statement(parsed, body, keep, highlights, tracks, include_highlights)
        return
    if statement.type == "labeled_statement":
        keep.add(statement.start_point.row + 1)
        nested = statement.named_children[-1]
        _collect_statement(parsed, nested, keep, highlights, tracks, include_highlights)
        return
    if statement.type in CONTROL_TYPES:
        _keep_range(keep, statement.start_point.row + 1, statement.end_point.row + 1)
        return
    if statement.type in STATEMENT_TYPES and track_matches:
        _keep_range(keep, statement.start_point.row + 1, statement.end_point.row + 1)


def _collect_if_chain(
    parsed: ParsedSource,
    if_node: Node,
    keep: set[int],
    highlights: dict[int, set[InlineHighlightSpan]],
    tracks: tuple[TrackPath, ...],
    include_highlights: bool,
) -> None:
    consequence = if_node.named_children[1]
    _keep_range(keep, if_node.start_point.row + 1, consequence.start_point.row + 1)
    if consequence.type == "compound_statement":
        keep.add(consequence.end_point.row + 1)
        _collect_from_container(parsed, consequence, keep, highlights, tracks, include_highlights)
    else:
        _collect_statement(parsed, consequence, keep, highlights, tracks, include_highlights)

    else_clause = _else_clause(if_node)
    if else_clause is None:
        return
    alternative = else_clause.named_children[-1]
    _keep_range(keep, else_clause.start_point.row + 1, alternative.start_point.row + 1)
    if alternative.type == "if_statement":
        _collect_if_chain(parsed, alternative, keep, highlights, tracks, include_highlights)
        return
    if alternative.type == "compound_statement":
        keep.add(alternative.end_point.row + 1)
        _collect_from_container(parsed, alternative, keep, highlights, tracks, include_highlights)
        return
    _collect_statement(parsed, alternative, keep, highlights, tracks, include_highlights)


def _record_track_highlights(
    parsed: ParsedSource,
    matches: tuple[Node, ...],
    highlights: dict[int, set[InlineHighlightSpan]],
) -> None:
    for match in matches:
        for line_no, start_column, end_column in parsed.source.inline_spans_for_byte_range(
            match.start_byte,
            match.end_byte,
        ):
            line_highlights = highlights.setdefault(line_no, set())
            line_highlights.add(
                InlineHighlightSpan(
                    start_column=start_column,
                    end_column=end_column,
                    kind="track_match",
                )
            )


def _collect_track_matches(parsed: ParsedSource, node: Node, tracks: tuple[TrackPath, ...]) -> tuple[Node, ...]:
    if not tracks:
        return ()
    normalized_tracks = {track.normalized for track in tracks}
    matches: list[Node] = []
    seen: set[tuple[int, int]] = set()
    stack = [node]
    while stack:
        current = stack.pop()
        candidate = _track_candidate_text(parsed, current)
        if candidate is not None and candidate in normalized_tracks:
            key = (current.start_byte, current.end_byte)
            if key not in seen:
                seen.add(key)
                matches.append(current)
        stack.extend(reversed(current.named_children))
    return tuple(matches)


def _track_candidate_text(parsed: ParsedSource, node: Node) -> str | None:
    if node.type == "field_expression":
        return "".join(node_text(parsed.source, node).split())
    if node.type == "identifier" and node.parent is not None and node.parent.type != "field_expression":
        return node_text(parsed.source, node)
    return None


def _container_statements(container: Node) -> list[Node]:
    if container.type == "compound_statement":
        return list(container.named_children)
    if container.type == "case_statement":
        return [child for child in container.named_children if _is_body_statement(child)]
    if container.type == "labeled_statement":
        return [container.named_children[-1]]
    return [container]


def _is_body_statement(node: Node) -> bool:
    return node.type.endswith("_statement") or node.type == "declaration"


def _case_body_container(case_node: Node) -> Node:
    for child in case_node.named_children:
        if child.type == "compound_statement":
            return child
    return case_node


def _else_clause(if_node: Node) -> Node | None:
    for child in if_node.named_children:
        if child.type == "else_clause":
            return child
    return None


def _keep_range(keep: set[int], start_line: int, end_line: int) -> None:
    keep.update(range(start_line, end_line + 1))
