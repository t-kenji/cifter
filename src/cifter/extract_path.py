from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from cifter.errors import CiftError
from cifter.model import (
    ExtractedLine,
    ExtractionResult,
    RouteSegment,
    normalize_condition_text,
    parse_route,
)
from cifter.parser import ParsedSource, condition_text, find_function, function_body, node_text


@dataclass(frozen=True)
class _RouteMatch:
    owner: Node
    owner_index: int
    kind: str
    branch: Node
    header_start_line: int
    header_end_line: int
    trim_end_byte: int | None = None
    selected_start_byte: int | None = None


def extract_path(parsed: ParsedSource, function_name: str, route: str) -> ExtractionResult:
    function_node = find_function(parsed, function_name)
    segments = parse_route(route)
    body = function_body(function_node)
    rendered: dict[int, str] = {}
    _keep_original_range(rendered, parsed, function_node.start_point.row + 1, body.start_point.row + 1)
    rendered[body.end_point.row + 1] = parsed.source.line_text(body.end_point.row + 1)
    _collect_path_from_container(parsed, body, segments, rendered)
    line_numbers = sorted(rendered)
    lines = tuple(ExtractedLine(line_no=line_no, text=rendered[line_no]) for line_no in line_numbers)
    return ExtractionResult(span=parsed.source.span_for_lines(line_numbers), lines=lines)


def _collect_path_from_container(
    parsed: ParsedSource,
    container: Node,
    segments: tuple[RouteSegment, ...],
    rendered: dict[int, str],
) -> None:
    statements = _container_statements(container)
    match = _find_unique_match(parsed, container, segments[0])
    if not _is_function_body(container):
        _keep_linear_statements(rendered, parsed, statements[: match.owner_index])

    if match.kind == "case":
        _render_switch_context(rendered, parsed, match.owner)
        rendered[match.header_start_line] = parsed.source.line_text(match.header_start_line)
        if len(segments) == 1:
            _keep_full_statement(rendered, parsed, match.branch)
            return
        _collect_path_from_container(parsed, match.branch, segments[1:], rendered)
        return

    _render_if_context(rendered, parsed, match)
    if len(segments) == 1:
        _keep_branch_body(rendered, parsed, match)
        _keep_linear_statements(rendered, parsed, statements[match.owner_index + 1 :])
        return

    _collect_path_from_container(parsed, match.branch, segments[1:], rendered)
    _keep_branch_closing(rendered, parsed, match)


def _find_unique_match(parsed: ParsedSource, container: Node, segment: RouteSegment) -> _RouteMatch:
    matches = _find_matches(parsed, container, segment)
    if not matches:
        raise CiftError(f"route に一致する枝が見つかりません: {segment.raw}")
    if len(matches) > 1:
        raise CiftError(f"route に一致する枝が複数あります: {segment.raw}")
    return matches[0]


def _find_matches(parsed: ParsedSource, container: Node, segment: RouteSegment) -> list[_RouteMatch]:
    matches: list[_RouteMatch] = []
    statements = _container_statements(container)
    for index, statement in enumerate(statements):
        if segment.kind in {"case", "default"} and statement.type == "switch_statement":
            for case_statement in _switch_cases(statement):
                if segment.kind == "case" and _case_label(parsed, case_statement) == segment.label:
                    matches.append(
                        _RouteMatch(
                            owner=statement,
                            owner_index=index,
                            kind="case",
                            branch=case_statement,
                            header_start_line=case_statement.start_point.row + 1,
                            header_end_line=case_statement.start_point.row + 1,
                            selected_start_byte=case_statement.start_byte,
                        )
                    )
                if segment.kind == "default" and _is_default_case(case_statement):
                    matches.append(
                        _RouteMatch(
                            owner=statement,
                            owner_index=index,
                            kind="case",
                            branch=case_statement,
                            header_start_line=case_statement.start_point.row + 1,
                            header_end_line=case_statement.start_point.row + 1,
                            selected_start_byte=case_statement.start_byte,
                        )
                    )
        if statement.type != "if_statement":
            continue
        if segment.kind == "if" and _normalized_if_condition(parsed, statement) == segment.condition:
            consequence = statement.named_children[1]
            matches.append(
                _RouteMatch(
                    owner=statement,
                    owner_index=index,
                    kind="if",
                    branch=consequence,
                    header_start_line=statement.start_point.row + 1,
                    header_end_line=consequence.start_point.row + 1,
                    trim_end_byte=_trim_end_byte(statement, consequence),
                    selected_start_byte=statement.start_byte,
                )
            )
        if segment.kind == "else":
            else_match = _final_else_match(statement, index)
            if else_match is not None:
                matches.append(else_match)
        if segment.kind == "else_if":
            matches.extend(_else_if_matches(parsed, statement, index, segment.condition or ""))
    return matches


def _else_if_matches(
    parsed: ParsedSource,
    if_node: Node,
    owner_index: int,
    condition: str,
) -> list[_RouteMatch]:
    matches: list[_RouteMatch] = []
    current = if_node
    while True:
        else_clause = _else_clause(current)
        if else_clause is None:
            return matches
        alternative = else_clause.named_children[-1]
        if alternative.type != "if_statement":
            return matches
        consequence = alternative.named_children[1]
        if _normalized_if_condition(parsed, alternative) == condition:
            matches.append(
                _RouteMatch(
                    owner=if_node,
                    owner_index=owner_index,
                    kind="else_if",
                    branch=consequence,
                    header_start_line=else_clause.start_point.row + 1,
                    header_end_line=consequence.start_point.row + 1,
                    trim_end_byte=_trim_end_byte(alternative, consequence),
                    selected_start_byte=alternative.start_byte,
                )
            )
        current = alternative


def _final_else_match(if_node: Node, owner_index: int) -> _RouteMatch | None:
    current = if_node
    while True:
        else_clause = _else_clause(current)
        if else_clause is None:
            return None
        alternative = else_clause.named_children[-1]
        if alternative.type == "if_statement":
            current = alternative
            continue
        return _RouteMatch(
            owner=if_node,
            owner_index=owner_index,
            kind="else",
            branch=alternative,
            header_start_line=else_clause.start_point.row + 1,
            header_end_line=alternative.start_point.row + 1,
        )


def _keep_branch_body(rendered: dict[int, str], parsed: ParsedSource, match: _RouteMatch) -> None:
    if match.kind == "case":
        _keep_full_statement(rendered, parsed, match.branch)
        return
    branch = match.branch
    if branch.type == "compound_statement":
        _keep_original_range(rendered, parsed, branch.start_point.row + 1, branch.end_point.row + 1)
        _keep_branch_closing(rendered, parsed, match)
        return
    _keep_original_range(rendered, parsed, branch.start_point.row + 1, branch.end_point.row + 1)


def _keep_branch_closing(rendered: dict[int, str], parsed: ParsedSource, match: _RouteMatch) -> None:
    _keep_compound_closing(rendered, parsed, match.branch, match.trim_end_byte)


def _keep_full_statement(rendered: dict[int, str], parsed: ParsedSource, statement: Node) -> None:
    _keep_original_range(rendered, parsed, statement.start_point.row + 1, statement.end_point.row + 1)


def _render_switch_context(rendered: dict[int, str], parsed: ParsedSource, switch_node: Node) -> None:
    body = switch_node.named_children[-1]
    _keep_original_range(rendered, parsed, switch_node.start_point.row + 1, body.start_point.row + 1)
    rendered[body.end_point.row + 1] = parsed.source.line_text(body.end_point.row + 1)


def _render_if_context(rendered: dict[int, str], parsed: ParsedSource, match: _RouteMatch) -> None:
    if match.kind == "if":
        _keep_original_range(rendered, parsed, match.header_start_line, match.header_end_line)
        return

    owner = match.owner
    owner_consequence = owner.named_children[1]
    _keep_original_range(rendered, parsed, owner.start_point.row + 1, owner_consequence.start_point.row + 1)
    _keep_compound_closing(
        rendered,
        parsed,
        owner_consequence,
        _trim_end_byte(owner, owner_consequence),
    )

    current = owner
    while True:
        else_clause = _else_clause(current)
        if else_clause is None:
            raise CiftError("else 連鎖を特定できません")

        alternative = else_clause.named_children[-1]
        if match.kind == "else" and alternative.start_byte == match.branch.start_byte:
            _keep_original_range(rendered, parsed, else_clause.start_point.row + 1, match.header_end_line)
            return
        if alternative.type != "if_statement":
            raise CiftError("else if 連鎖を特定できません")

        consequence = alternative.named_children[1]
        if match.kind == "else_if" and alternative.start_byte == match.selected_start_byte:
            _keep_original_range(rendered, parsed, else_clause.start_point.row + 1, match.header_end_line)
            return

        _keep_original_range(rendered, parsed, else_clause.start_point.row + 1, consequence.start_point.row + 1)
        _keep_compound_closing(
            rendered,
            parsed,
            consequence,
            _trim_end_byte(alternative, consequence),
        )
        current = alternative


def _keep_compound_closing(
    rendered: dict[int, str],
    parsed: ParsedSource,
    branch: Node,
    trim_end_byte: int | None,
) -> None:
    if branch.type != "compound_statement":
        return
    line_no = branch.end_point.row + 1
    if trim_end_byte is None:
        rendered[line_no] = parsed.source.line_text(line_no)
        return
    rendered[line_no] = parsed.source.slice_from_line_start(line_no, trim_end_byte)


def _keep_linear_statements(
    rendered: dict[int, str],
    parsed: ParsedSource,
    statements: list[Node],
) -> None:
    for statement in statements:
        if not _is_branching_statement(statement):
            _keep_full_statement(rendered, parsed, statement)


def _keep_original_range(
    rendered: dict[int, str],
    parsed: ParsedSource,
    start_line: int,
    end_line: int,
) -> None:
    for line_no in range(start_line, end_line + 1):
        rendered[line_no] = parsed.source.line_text(line_no)


def _container_statements(container: Node) -> list[Node]:
    if container.type == "compound_statement":
        return list(container.named_children)
    if container.type == "case_statement":
        return [child for child in container.named_children if _is_body_statement(child)]
    return [container]


def _is_body_statement(node: Node) -> bool:
    return node.type.endswith("_statement") or node.type == "declaration"


def _switch_cases(switch_node: Node) -> list[Node]:
    body = switch_node.named_children[-1]
    return [child for child in body.named_children if child.type == "case_statement"]


def _case_label(parsed: ParsedSource, case_node: Node) -> str | None:
    if _is_default_case(case_node):
        return None
    for child in case_node.named_children:
        if child.type == "identifier":
            return node_text(parsed.source, child)
        if child.type.endswith("_expression") or child.type.endswith("_literal"):
            return node_text(parsed.source, child).strip()
    return None


def _is_default_case(case_node: Node) -> bool:
    return bool(case_node.children) and case_node.children[0].type == "default"


def _normalized_if_condition(parsed: ParsedSource, if_node: Node) -> str:
    condition_node = if_node.named_children[0]
    return normalize_condition_text(condition_text(parsed.source, condition_node))


def _else_clause(if_node: Node) -> Node | None:
    for child in if_node.named_children:
        if child.type == "else_clause":
            return child
    return None


def _trim_end_byte(if_node: Node, branch: Node) -> int | None:
    else_clause = _else_clause(if_node)
    if else_clause is None:
        return None
    if branch.end_point.row != else_clause.start_point.row:
        return None
    return branch.end_byte


def _is_branching_statement(node: Node) -> bool:
    return node.type in {"if_statement", "switch_statement", "for_statement", "while_statement", "do_statement"}


def _is_function_body(node: Node) -> bool:
    return node.type == "compound_statement" and node.parent is not None and node.parent.type == "function_definition"
