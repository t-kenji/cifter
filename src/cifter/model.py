from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Literal

from cifter.errors import CiftError

TRACK_PATH_PATTERN = re.compile(r"^[A-Za-z_]\w*(?:(?:->|\.)[A-Za-z_]\w*)*$")
ParseDiagnosticCategory = Literal["language", "parse", "preprocess", "input"]
ParseQualityLevel = Literal["clean", "degraded"]
LanguageMode = Literal["auto", "c", "cpp"]
LanguageResolution = Literal["explicit", "extension", "quality"]
InlineHighlightKind = Literal["track_match"]
RouteSegmentKind = Literal["case", "default", "else_if", "else", "for", "while", "do_while", "if"]


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
class ParseQualityReport:
    level: ParseQualityLevel
    diagnostics: tuple[ParseDiagnostic, ...] = ()

    @classmethod
    def from_diagnostics(cls, diagnostics: tuple[ParseDiagnostic, ...]) -> ParseQualityReport:
        if diagnostics:
            return cls(level="degraded", diagnostics=diagnostics)
        return cls(level="clean", diagnostics=())


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
    label: str | None = None
    condition: str | None = None

    @classmethod
    def parse(cls, raw: str) -> RouteSegment:
        value = raw.strip()
        if not value:
            raise CiftError("空の route 要素は指定できません")
        if value.startswith("case "):
            label = value[5:].strip()
            if not label:
                raise CiftError(f"不正な --route 要素です: {raw}")
            return cls(kind="case", raw=value, label=label)
        if value == "default":
            return cls(kind="default", raw=value)
        if value.startswith("else if "):
            condition = value[8:].strip()
            if not condition:
                raise CiftError(f"不正な --route 要素です: {raw}")
            return cls(
                kind="else_if",
                raw=value,
                condition=normalize_condition_text(condition),
            )
        if value == "else":
            return cls(kind="else", raw=value)
        if value == "for":
            return cls(kind="for", raw=value)
        if value.startswith("do while "):
            condition = value[9:].strip()
            if not condition:
                raise CiftError(f"不正な --route 要素です: {raw}")
            return cls(kind="do_while", raw=value, condition=normalize_condition_text(condition))
        if value.startswith("while "):
            condition = value[6:].strip()
            if not condition:
                raise CiftError(f"不正な --route 要素です: {raw}")
            return cls(kind="while", raw=value, condition=normalize_condition_text(condition))
        if value.startswith("if "):
            condition = value[3:].strip()
            if not condition:
                raise CiftError(f"不正な --route 要素です: {raw}")
            return cls(kind="if", raw=value, condition=normalize_condition_text(condition))
        raise CiftError(f"不正な --route 要素です: {raw}")


def normalize_condition_text(text: str) -> str:
    value = "".join(text.split())
    while value.startswith("(") and value.endswith(")") and _covers_entire_text(value):
        value = value[1:-1]
    return value


def _covers_entire_text(text: str) -> bool:
    depth = 0
    for index, char in enumerate(text):
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
    segments = tuple(RouteSegment.parse(part) for part in parts)
    for left, right in pairwise(segments):
        if left.kind == "else" and right.kind == "if":
            raise CiftError("`else > if ...` は非対応です。`else if ...` を使ってください")
    return segments


def _split_route(route: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(route):
        char = route[index]
        if char == ">":
            lookahead = index + 1
            while lookahead < len(route) and route[lookahead].isspace():
                lookahead += 1
            tail = route[lookahead:]
            if current and _starts_route_segment(tail):
                parts.append("".join(current).strip())
                current = []
                index = lookahead
                continue
        current.append(char)
        index += 1
    if current:
        parts.append("".join(current).strip())
    return [part for part in parts if part]


def _starts_route_segment(value: str) -> bool:
    return any(
        value.startswith(prefix)
        for prefix in (
            "case ",
            "default",
            "if ",
            "else ",
            "else",
            "else if ",
            "for",
            "while ",
            "do while ",
        )
    )
