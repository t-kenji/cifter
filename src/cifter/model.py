from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from cifter.errors import CiftError

TRACK_PATH_PATTERN = re.compile(r"^[A-Za-z_]\w*(?:(?:->|\.)[A-Za-z_]\w*)*$")
SUPPORTED_SOURCE_EXTENSIONS = {".c", ".h", ".cc", ".cpp", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++"}
ParseDiagnosticCategory = Literal["language", "parse", "preprocess", "input"]
LanguageMode = Literal["auto", "c", "cpp"]
LanguageResolution = Literal["explicit", "extension", "quality"]
InlineHighlightKind = Literal["track_match"]
RouteSegmentKind = Literal["case", "default", "else_if", "else", "for", "while", "do_while", "if"]
FormatMode = Literal["auto", "text", "json"]
CommandName = Literal["function", "flow", "route"]
DiagnosticSeverity = Literal["error", "warning"]
_RoutePayloadMode = Literal["none", "required", "optional"]


@dataclass(frozen=True)
class SourceSpan:
    file: Path
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ParseDiagnostic:
    category: ParseDiagnosticCategory
    code: str
    message: str
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class InlineHighlightSpan:
    start_column: int
    end_column: int
    kind: InlineHighlightKind


@dataclass(frozen=True)
class ExtractedLine:
    line_no: int
    text: str
    highlights: tuple[InlineHighlightSpan, ...] = ()
    omitted_after_indent: str | None = None


@dataclass(frozen=True)
class ExtractionResult:
    span: SourceSpan
    lines: tuple[ExtractedLine, ...]


@dataclass(frozen=True)
class RunDiagnostic:
    severity: DiagnosticSeverity
    code: str
    message: str
    file: Path | None = None


@dataclass(frozen=True)
class ExtractionItem:
    file: Path
    symbol: str
    kind: CommandName
    span: SourceSpan
    language: str
    lines: tuple[ExtractedLine, ...]
    diagnostics: tuple[ParseDiagnostic, ...] = ()
    routes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunResult:
    tool_version: str
    command: CommandName
    inputs: tuple[Path, ...]
    results: tuple[ExtractionItem, ...]
    diagnostics: tuple[RunDiagnostic, ...] = ()


@dataclass(frozen=True)
class TrackPath:
    raw: str
    normalized: str

    @classmethod
    def parse(cls, raw: str) -> TrackPath:
        value = raw.strip()
        if not value or not TRACK_PATH_PATTERN.fullmatch(value):
            raise CiftError(f"不正な --track です: {raw}")
        return cls(raw=value, normalized="".join(value.split()))


@dataclass(frozen=True)
class RouteSegment:
    kind: RouteSegmentKind
    raw: str
    payload: str | None = None
    normalized_payload: str | None = None

    @classmethod
    def parse(cls, raw: str) -> RouteSegment:
        value = raw.strip()
        if not value:
            raise CiftError("空の route 要素は指定できません")
        segment = _parse_route_segment(value)
        if segment is not None:
            return segment
        raise CiftError(f"不正な --route 要素です: {raw}")


@dataclass(frozen=True)
class _RouteSegmentSpec:
    keyword: str
    kind: RouteSegmentKind
    payload_mode: _RoutePayloadMode = "none"
    normalizer: Callable[[str], str] | None = None


def normalize_condition_text(text: str) -> str:
    value = normalize_loop_header_text(text)
    while value.startswith("(") and value.endswith(")") and _covers_entire_text(value):
        value = normalize_loop_header_text(value[1:-1])
    return value


def normalize_loop_header_text(text: str) -> str:
    return _collapse_whitespace_preserving_literals(text.strip())


_ROUTE_SEGMENT_SPECS = (
    _RouteSegmentSpec("case", "case", "required", str.strip),
    _RouteSegmentSpec("default", "default"),
    _RouteSegmentSpec("else-if", "else_if", "required", normalize_condition_text),
    _RouteSegmentSpec("else", "else"),
    _RouteSegmentSpec("for", "for"),
    _RouteSegmentSpec("for", "for", "optional", normalize_loop_header_text),
    _RouteSegmentSpec("while", "while"),
    _RouteSegmentSpec("while", "while", "optional", normalize_condition_text),
    _RouteSegmentSpec("do-while", "do_while"),
    _RouteSegmentSpec("do-while", "do_while", "optional", normalize_condition_text),
    _RouteSegmentSpec("if", "if", "required", normalize_condition_text),
)


def _parse_route_segment(value: str) -> RouteSegment | None:
    for spec in _ROUTE_SEGMENT_SPECS:
        matched, payload = _payload_for_route_spec(value, spec)
        if not matched:
            continue
        normalized = payload
        if payload is not None and spec.normalizer is not None:
            normalized = spec.normalizer(payload)
        return RouteSegment(
            kind=spec.kind,
            raw=value,
            payload=payload,
            normalized_payload=normalized,
        )
    return None


def _covers_entire_text(text: str) -> bool:
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and index != len(text) - 1:
                return False
        if depth < 0:
            return False
    return depth == 0


def parse_route(route: str) -> tuple[RouteSegment, ...]:
    parts = _split_route(route)
    if not parts:
        raise CiftError("空の --route は指定できません")
    return tuple(RouteSegment.parse(part) for part in parts)


def _split_route(route: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    bracket_depth = 0
    quote: str | None = None
    escaped = False
    ended_with_separator = False
    for char in route.strip():
        if quote is not None:
            current.append(char)
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            continue
        if char == "[":
            bracket_depth += 1
            current.append(char)
            continue
        if char == "]":
            bracket_depth -= 1
            if bracket_depth < 0:
                raise CiftError(f"不正な --route です: {route}")
            current.append(char)
            continue
        if char == "/" and bracket_depth == 0:
            part = "".join(current).strip()
            if not part:
                raise CiftError("空の route 要素は指定できません")
            parts.append(part)
            current = []
            ended_with_separator = True
            continue
        current.append(char)
        ended_with_separator = False
    if quote is not None or bracket_depth != 0:
        raise CiftError(f"不正な --route です: {route}")
    if ended_with_separator:
        raise CiftError("空の route 要素は指定できません")
    if current:
        part = "".join(current).strip()
        if not part:
            raise CiftError("空の route 要素は指定できません")
        parts.append(part)
    return parts


def _payload_for_route_spec(value: str, spec: _RouteSegmentSpec) -> tuple[bool, str | None]:
    if spec.payload_mode == "none":
        return value == spec.keyword, None
    if value == spec.keyword:
        if spec.payload_mode == "required":
            raise CiftError(f"不正な --route 要素です: {value}")
        return True, None
    payload = _extract_payload(value, spec.keyword)
    if payload is None:
        return False, None
    if not payload.strip():
        raise CiftError(f"不正な --route 要素です: {value}")
    return True, payload


def _extract_payload(value: str, keyword: str) -> str | None:
    if not value.startswith(f"{keyword}["):
        return None
    tail = value[len(keyword) :]
    if not tail or tail[0] != "[":
        return None
    end_index = _find_matching_bracket(tail)
    if end_index != len(tail) - 1:
        raise CiftError(f"不正な --route 要素です: {value}")
    return tail[1:end_index]


def _find_matching_bracket(text: str) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "[":
            depth += 1
            continue
        if char == "]":
            depth -= 1
            if depth == 0:
                return index
            if depth < 0:
                break
    raise CiftError(f"不正な --route 要素です: {text}")


def _collapse_whitespace_preserving_literals(text: str) -> str:
    result: list[str] = []
    quote: str | None = None
    escaped = False
    pending_space = False
    for char in text:
        if quote is not None:
            result.append(char)
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            if pending_space and result:
                result.append(" ")
                pending_space = False
            result.append(char)
            quote = char
            continue
        if char.isspace():
            pending_space = bool(result)
            continue
        if pending_space and result:
            result.append(" ")
            pending_space = False
        result.append(char)
    return "".join(result)
