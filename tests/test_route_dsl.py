from __future__ import annotations

import pytest

from cifter.errors import CiftError
from cifter.model import parse_route


def test_parse_route_supports_canonical_segments() -> None:
    segments = parse_route(" case[CMD_LOOP] / while / if[(ctx->retry_count == 1)] ")

    assert [segment.kind for segment in segments] == ["case", "while", "if"]
    assert segments[0].payload == "CMD_LOOP"
    assert segments[0].normalized_payload == "CMD_LOOP"
    assert segments[1].payload is None
    assert segments[2].normalized_payload == "ctx->retry_count == 1"


def test_parse_route_supports_for_and_else_if_payloads() -> None:
    segments = parse_route("case[CMD_LOOP]/for[i = 0; i < 4; i++]/else-if[(ret == 11)]")

    assert [segment.kind for segment in segments] == ["case", "for", "else_if"]
    assert segments[1].normalized_payload == "i = 0; i < 4; i++"
    assert segments[2].normalized_payload == "ret == 11"


def test_parse_route_ignores_delimiters_inside_nested_payloads_and_literals() -> None:
    segments = parse_route(
        r"""if[arr[index_map['/']] == ']']/if[strcmp(path, "/") == 0]/if[table[lookup("]")] > 0]"""
    )

    assert len(segments) == 3
    assert segments[0].payload == "arr[index_map['/']] == ']'"
    assert segments[1].payload == 'strcmp(path, "/") == 0'
    assert segments[2].payload == 'table[lookup("]")] > 0'


@pytest.mark.parametrize(
    "route",
    [
        "default[x]",
        "else[x]",
        "if[]",
        "case",
        "case CMD_LOOP > while",
        "else if[(ret == 11)]",
        "do while[(state < 31)]",
        "case[CMD_LOOP]/",
    ],
)
def test_parse_route_rejects_invalid_inputs(route: str) -> None:
    with pytest.raises(CiftError):
        parse_route(route)
