from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import IntEnum

from tree_sitter import Node

from cifter.errors import CiftError
from cifter.model import (
    ExtractedLine,
    ExtractionResult,
    RouteSegment,
    normalize_condition_text,
    normalize_loop_header_text,
)
from cifter.omission import attach_omission_markers
from cifter.parser import ParsedSource, function_body, node_text
from cifter.tree_helpers import (
    case_body_container,
    container_statements,
    else_clause,
    is_branching_statement,
    is_function_body,
)


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


class _RenderPriority(IntEnum):
    TRIMMED = 1
    ORIGINAL = 2


@dataclass(frozen=True)
class _RenderedLine:
    text: str
    priority: _RenderPriority


def extract_route_node(
    parsed: ParsedSource,
    function_node: Node,
    routes: Sequence[tuple[RouteSegment, ...]],
) -> ExtractionResult:
    route_values = tuple(routes)
    if not route_values:
        raise CiftError("空の --route は指定できません")
    body = function_body(function_node)
    rendered: dict[int, _RenderedLine] = {}
    _keep_original_range(
        rendered, parsed, function_node.start_point.row + 1, body.start_point.row + 1
    )
    _record_original_line(rendered, parsed, body.end_point.row + 1)
    for segments in route_values:
        route_rendered: dict[int, _RenderedLine] = {}
        _collect_path_from_container(parsed, body, segments, route_rendered)
        _merge_rendered(rendered, route_rendered)
    line_numbers = sorted(rendered)
    lines = tuple(
        ExtractedLine(line_no=line_no, text=rendered[line_no].text) for line_no in line_numbers
    )
    lines = attach_omission_markers(parsed.source, lines)
    return ExtractionResult(span=parsed.source.span_for_lines(line_numbers), lines=lines)


def _collect_path_from_container(
    parsed: ParsedSource,
    container: Node,
    segments: tuple[RouteSegment, ...],
    rendered: dict[int, _RenderedLine],
) -> None:
    statements = container_statements(container)
    match = _find_first_match(parsed, container, segments[0])
    if not is_function_body(container):
        _keep_linear_statements(rendered, parsed, statements[: match.owner_index])

    if match.kind == "case":
        _render_switch_context(rendered, parsed, match.owner)
        _record_original_line(rendered, parsed, match.header_start_line)
        body = case_body_container(match.branch)
        if len(segments) == 1:
            _keep_original_range(
                rendered, parsed, match.branch.start_point.row + 1, match.branch.end_point.row + 1
            )
            return
        if body is not match.branch:
            _record_original_line(rendered, parsed, body.start_point.row + 1)
        _collect_path_from_container(parsed, body, segments[1:], rendered)
        if body is not match.branch:
            _record_original_line(rendered, parsed, body.end_point.row + 1)
        return

    if match.kind in {"if", "else", "else_if"}:
        _render_if_context(rendered, parsed, match)
    else:
        _keep_original_range(rendered, parsed, match.header_start_line, match.header_end_line)

    if len(segments) == 1:
        _keep_match_body(rendered, parsed, match)
        _keep_trailing_linear_statements(rendered, parsed, statements[match.owner_index + 1 :])
        return

    _collect_path_from_container(parsed, match.branch, segments[1:], rendered)
    _keep_match_closing(rendered, parsed, match)


def _find_first_match(parsed: ParsedSource, container: Node, segment: RouteSegment) -> _RouteMatch:
    matches = _find_matches(parsed, container, segment)
    if matches:
        return matches[0]
    raise CiftError(f"route に一致する枝が見つかりません: {segment.raw}")


def _find_matches(
    parsed: ParsedSource,
    container: Node,
    segment: RouteSegment,
) -> list[_RouteMatch]:
    matches: list[_RouteMatch] = []
    statements = container_statements(container)
    for index, statement in enumerate(statements):
        if segment.kind in {"case", "default"} and statement.type == "switch_statement":
            _collect_switch_matches(matches, parsed, statement, index, segment)
        loop_match = _loop_match(parsed, statement, index, segment)
        if loop_match is not None:
            matches.append(loop_match)
        if statement.type != "if_statement":
            continue
        if (
            segment.kind == "if"
            and _normalized_if_condition(parsed, statement) == segment.normalized_payload
        ):
            consequence = statement.named_children[1]
            matches.append(
                _route_match(
                    statement,
                    index,
                    "if",
                    consequence,
                    header_end=consequence,
                    trim_end_byte=_trim_end_byte(statement, consequence),
                    selected_start_byte=statement.start_byte,
                )
            )
        if segment.kind == "else":
            else_match = _final_else_match(statement, index)
            if else_match is not None:
                matches.append(else_match)
        if segment.kind == "else_if":
            matches.extend(
                _else_if_matches(parsed, statement, index, segment.normalized_payload or "")
            )
    return matches


def _else_if_matches(
    parsed: ParsedSource,
    if_node: Node,
    owner_index: int,
    condition: str,
) -> list[_RouteMatch]:
    matches: list[_RouteMatch] = []
    for clause, alternative in _iter_else_chain(if_node):
        if alternative.type != "if_statement":
            return matches
        consequence = alternative.named_children[1]
        if _normalized_if_condition(parsed, alternative) == condition:
            matches.append(
                _route_match(
                    if_node,
                    owner_index,
                    "else_if",
                    consequence,
                    header_start=clause,
                    header_end=consequence,
                    trim_end_byte=_trim_end_byte(alternative, consequence),
                    selected_start_byte=alternative.start_byte,
                )
            )
    return matches


def _final_else_match(if_node: Node, owner_index: int) -> _RouteMatch | None:
    for clause, alternative in _iter_else_chain(if_node):
        if alternative.type == "if_statement":
            continue
        return _route_match(
            if_node, owner_index, "else", alternative, header_start=clause, header_end=alternative
        )
    return None


def _keep_match_body(
    rendered: dict[int, _RenderedLine],
    parsed: ParsedSource,
    match: _RouteMatch,
) -> None:
    if match.kind == "case":
        _keep_original_range(
            rendered, parsed, match.branch.start_point.row + 1, match.branch.end_point.row + 1
        )
        return
    branch = match.branch
    if branch.type == "compound_statement":
        _keep_original_range(rendered, parsed, branch.start_point.row + 1, branch.end_point.row + 1)
        _keep_match_closing(rendered, parsed, match)
        return
    _keep_original_range(rendered, parsed, branch.start_point.row + 1, branch.end_point.row + 1)
    if match.kind == "do_while":
        _record_original_line(rendered, parsed, match.owner.end_point.row + 1)


def _keep_match_closing(
    rendered: dict[int, _RenderedLine],
    parsed: ParsedSource,
    match: _RouteMatch,
) -> None:
    if match.kind == "do_while":
        _record_original_line(rendered, parsed, match.owner.end_point.row + 1)
        return
    _keep_compound_closing(rendered, parsed, match.branch, match.trim_end_byte)


def _render_switch_context(
    rendered: dict[int, _RenderedLine],
    parsed: ParsedSource,
    switch_node: Node,
) -> None:
    body = switch_node.named_children[-1]
    _keep_original_range(
        rendered, parsed, switch_node.start_point.row + 1, body.start_point.row + 1
    )
    _record_original_line(rendered, parsed, body.end_point.row + 1)


def _render_if_context(
    rendered: dict[int, _RenderedLine],
    parsed: ParsedSource,
    match: _RouteMatch,
) -> None:
    if match.kind == "if":
        _keep_original_range(rendered, parsed, match.header_start_line, match.header_end_line)
        return

    owner = match.owner
    owner_consequence = owner.named_children[1]
    _keep_original_range(
        rendered, parsed, owner.start_point.row + 1, owner_consequence.start_point.row + 1
    )
    _keep_compound_closing(
        rendered,
        parsed,
        owner_consequence,
        _trim_end_byte(owner, owner_consequence),
    )

    for clause, alternative in _iter_else_chain(owner):
        if match.kind == "else" and alternative.start_byte == match.branch.start_byte:
            _keep_original_range(
                rendered, parsed, clause.start_point.row + 1, match.header_end_line
            )
            return
        if alternative.type != "if_statement":
            raise CiftError("else if 連鎖を特定できません")

        consequence = alternative.named_children[1]
        if match.kind == "else_if" and alternative.start_byte == match.selected_start_byte:
            _keep_original_range(
                rendered, parsed, clause.start_point.row + 1, match.header_end_line
            )
            return

        _keep_original_range(
            rendered, parsed, clause.start_point.row + 1, consequence.start_point.row + 1
        )
        _keep_compound_closing(
            rendered,
            parsed,
            consequence,
            _trim_end_byte(alternative, consequence),
        )
    raise CiftError("else 連鎖を特定できません")
def _keep_compound_closing(rendered: dict[int, _RenderedLine], parsed: ParsedSource, branch: Node, trim_end_byte: int | None) -> None:
    if branch.type != "compound_statement":
        return
    line_no = branch.end_point.row + 1
    if trim_end_byte is None:
        _record_original_line(rendered, parsed, line_no)
        return
    _record_line(
        rendered,
        line_no,
        parsed.source.slice_from_line_start(line_no, trim_end_byte),
        _RenderPriority.TRIMMED,
    )


def _keep_linear_statements(rendered: dict[int, _RenderedLine], parsed: ParsedSource, statements: list[Node]) -> None:
    for statement in statements:
        if not is_branching_statement(statement):
            _keep_original_range(
                rendered, parsed, statement.start_point.row + 1, statement.end_point.row + 1
            )


def _keep_trailing_linear_statements(rendered: dict[int, _RenderedLine], parsed: ParsedSource, statements: list[Node]) -> None:
    for statement in statements:
        if is_branching_statement(statement):
            return
        _keep_original_range(
            rendered, parsed, statement.start_point.row + 1, statement.end_point.row + 1
        )


def _keep_original_range(rendered: dict[int, _RenderedLine], parsed: ParsedSource, start_line: int, end_line: int) -> None:
    for line_no in range(start_line, end_line + 1):
        _record_original_line(rendered, parsed, line_no)


def _record_original_line(rendered: dict[int, _RenderedLine], parsed: ParsedSource, line_no: int) -> None:
    _record_line(rendered, line_no, parsed.source.line_text(line_no), _RenderPriority.ORIGINAL)


def _record_line(rendered: dict[int, _RenderedLine], line_no: int, text: str, priority: _RenderPriority) -> None:
    rendered[line_no] = _RenderedLine(text=text, priority=priority)


def _merge_rendered(rendered: dict[int, _RenderedLine], route_rendered: dict[int, _RenderedLine]) -> None:
    for line_no, item in route_rendered.items():
        current = rendered.get(line_no)
        if (
            current is None
            or item.priority > current.priority
            or (item.priority == current.priority and len(item.text) > len(current.text))
        ):
            rendered[line_no] = item


def _switch_cases(switch_node: Node) -> list[Node]: return [child for child in switch_node.named_children[-1].named_children if child.type == "case_statement"]


def _collect_switch_matches(matches: list[_RouteMatch], parsed: ParsedSource, statement: Node, owner_index: int, segment: RouteSegment) -> None:
    for case_statement in _switch_cases(statement):
        if (
            segment.kind == "case"
            and _case_label(parsed, case_statement) == segment.normalized_payload
        ):
            matches.append(
                _route_match(
                    statement, owner_index, "case", case_statement, header_start=case_statement
                )
            )
        if segment.kind == "default" and _is_default_case(case_statement):
            matches.append(
                _route_match(
                    statement, owner_index, "case", case_statement, header_start=case_statement
                )
            )


def _loop_match(parsed: ParsedSource, statement: Node, owner_index: int, segment: RouteSegment) -> _RouteMatch | None:
    if segment.kind == "for" and statement.type == "for_statement":
        branch = statement.named_children[-1]
        normalizer = _normalized_for_header
    elif segment.kind == "while" and statement.type == "while_statement":
        branch = statement.named_children[-1]
        normalizer = _normalized_while_condition
    elif segment.kind == "do_while" and statement.type == "do_statement":
        branch = statement.named_children[0]
        normalizer = _normalized_do_while_condition
    else:
        return None
    if (
        segment.normalized_payload is not None
        and normalizer(parsed, statement) != segment.normalized_payload
    ):
        return None
    return _route_match(statement, owner_index, segment.kind, branch, header_end=branch)


def _route_match(owner: Node, owner_index: int, kind: str, branch: Node, *, header_start: Node | None = None, header_end: Node | None = None, trim_end_byte: int | None = None, selected_start_byte: int | None = None) -> _RouteMatch:
    return _RouteMatch(
        owner=owner,
        owner_index=owner_index,
        kind=kind,
        branch=branch,
        header_start_line=(header_start or owner).start_point.row + 1,
        header_end_line=(header_end or header_start or branch).start_point.row + 1,
        trim_end_byte=trim_end_byte,
        selected_start_byte=selected_start_byte or branch.start_byte,
    )


def _iter_else_chain(if_node: Node) -> Iterator[tuple[Node, Node]]:
    current = if_node
    while clause := else_clause(current):
        alternative = clause.named_children[-1]
        yield clause, alternative
        if alternative.type != "if_statement":
            return
        current = alternative


def _case_label(parsed: ParsedSource, case_node: Node) -> str | None:
    if _is_default_case(case_node):
        return None
    for child in case_node.named_children:
        if child.type in {"identifier", "field_identifier", "qualified_identifier"}:
            return node_text(parsed.source, child)
        if child.type.endswith("_expression") or child.type.endswith("_literal"):
            return node_text(parsed.source, child).strip()
    return None


def _is_default_case(case_node: Node) -> bool: return bool(case_node.children) and case_node.children[0].type == "default"


def _normalized_if_condition(parsed: ParsedSource, if_node: Node) -> str:
    return normalize_condition_text(node_text(parsed.source, if_node.named_children[0]))


def _normalized_for_header(parsed: ParsedSource, for_node: Node) -> str:
    body = for_node.named_children[-1]
    header = parsed.source.text_bytes[for_node.start_byte : body.start_byte].decode("utf-8")
    open_index = header.find("(")
    close_index = header.rfind(")")
    if open_index == -1 or close_index == -1 or close_index < open_index:
        raise CiftError("for ヘッダを特定できません")
    return normalize_loop_header_text(header[open_index + 1 : close_index])


def _normalized_while_condition(parsed: ParsedSource, while_node: Node) -> str:
    return normalize_condition_text(node_text(parsed.source, while_node.named_children[0]))


def _normalized_do_while_condition(parsed: ParsedSource, do_node: Node) -> str:
    return normalize_condition_text(node_text(parsed.source, do_node.named_children[1]))


def _trim_end_byte(if_node: Node, branch: Node) -> int | None:
    clause = else_clause(if_node)
    if clause is None:
        return None
    if branch.end_point.row != clause.start_point.row:
        return None
    return branch.end_byte
