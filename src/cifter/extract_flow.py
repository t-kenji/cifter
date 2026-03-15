from __future__ import annotations

from tree_sitter import Node

from cifter.model import ExtractedLine, ExtractionResult, TrackPath
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


def extract_flow(parsed: ParsedSource, function_name: str, tracks: tuple[TrackPath, ...]) -> ExtractionResult:
    function_node = find_function(parsed, function_name)
    body = function_body(function_node)
    keep: set[int] = set()
    _keep_range(keep, function_node.start_point.row + 1, body.start_point.row + 1)
    keep.add(body.end_point.row + 1)
    _collect_from_container(parsed, body, keep, tracks)
    line_numbers = sorted(keep)
    lines = tuple(
        ExtractedLine(line_no=line_no, text=parsed.source.line_text(line_no))
        for line_no in line_numbers
    )
    return ExtractionResult(span=parsed.source.span_for_lines(line_numbers), lines=lines)


def _collect_from_container(
    parsed: ParsedSource,
    container: Node,
    keep: set[int],
    tracks: tuple[TrackPath, ...],
) -> None:
    for statement in _container_statements(container):
        _collect_statement(parsed, statement, keep, tracks)


def _collect_statement(
    parsed: ParsedSource,
    statement: Node,
    keep: set[int],
    tracks: tuple[TrackPath, ...],
) -> None:
    if statement.type == "switch_statement":
        body = statement.named_children[-1]
        _keep_range(keep, statement.start_point.row + 1, body.start_point.row + 1)
        keep.add(body.end_point.row + 1)
        _collect_from_container(parsed, body, keep, tracks)
        return
    if statement.type == "case_statement":
        keep.add(statement.start_point.row + 1)
        _collect_from_container(parsed, statement, keep, tracks)
        return
    if statement.type == "if_statement":
        _collect_if_chain(parsed, statement, keep, tracks)
        return
    if statement.type in {"for_statement", "while_statement"}:
        body = statement.named_children[-1]
        _keep_range(keep, statement.start_point.row + 1, body.start_point.row + 1)
        if body.type == "compound_statement":
            keep.add(body.end_point.row + 1)
            _collect_from_container(parsed, body, keep, tracks)
        else:
            _collect_statement(parsed, body, keep, tracks)
        return
    if statement.type == "do_statement":
        body = statement.named_children[0]
        keep.add(statement.start_point.row + 1)
        keep.add(statement.end_point.row + 1)
        if body.type == "compound_statement":
            keep.add(body.end_point.row + 1)
            _collect_from_container(parsed, body, keep, tracks)
        else:
            _collect_statement(parsed, body, keep, tracks)
        return
    if statement.type == "labeled_statement":
        keep.add(statement.start_point.row + 1)
        nested = statement.named_children[-1]
        _collect_statement(parsed, nested, keep, tracks)
        return
    if statement.type in CONTROL_TYPES:
        _keep_range(keep, statement.start_point.row + 1, statement.end_point.row + 1)
        return
    if statement.type in STATEMENT_TYPES and _matches_track(parsed, statement, tracks):
        _keep_range(keep, statement.start_point.row + 1, statement.end_point.row + 1)


def _collect_if_chain(
    parsed: ParsedSource,
    if_node: Node,
    keep: set[int],
    tracks: tuple[TrackPath, ...],
) -> None:
    consequence = if_node.named_children[1]
    _keep_range(keep, if_node.start_point.row + 1, consequence.start_point.row + 1)
    if consequence.type == "compound_statement":
        keep.add(consequence.end_point.row + 1)
        _collect_from_container(parsed, consequence, keep, tracks)
    else:
        _collect_statement(parsed, consequence, keep, tracks)

    else_clause = _else_clause(if_node)
    if else_clause is None:
        return
    alternative = else_clause.named_children[-1]
    _keep_range(keep, else_clause.start_point.row + 1, alternative.start_point.row + 1)
    if alternative.type == "if_statement":
        _collect_if_chain(parsed, alternative, keep, tracks)
        return
    if alternative.type == "compound_statement":
        keep.add(alternative.end_point.row + 1)
        _collect_from_container(parsed, alternative, keep, tracks)
        return
    _collect_statement(parsed, alternative, keep, tracks)


def _matches_track(parsed: ParsedSource, statement: Node, tracks: tuple[TrackPath, ...]) -> bool:
    if not tracks:
        return False
    candidates = _collect_track_candidates(parsed, statement)
    return any(track.normalized in candidates for track in tracks)


def _collect_track_candidates(parsed: ParsedSource, node: Node) -> set[str]:
    candidates: set[str] = set()
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == "field_expression":
            candidates.add(node_text(parsed.source, current).replace(" ", ""))
        elif current.type == "identifier" and current.parent is not None and current.parent.type != "field_expression":
            candidates.add(node_text(parsed.source, current))
        stack.extend(reversed(current.named_children))
    return candidates


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


def _else_clause(if_node: Node) -> Node | None:
    for child in if_node.named_children:
        if child.type == "else_clause":
            return child
    return None


def _keep_range(keep: set[int], start_line: int, end_line: int) -> None:
    keep.update(range(start_line, end_line + 1))
