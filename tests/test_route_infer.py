from __future__ import annotations

import json
from pathlib import Path

import pytest
from tree_sitter import Node

from cifter import run as run_module
from cifter.cli import app
from cifter.errors import CiftError
from cifter.parser import ParsedSource
from tests.support import (
    AMBIGUOUS_LINE_ROUTE_SOURCE,
    ELSE_SOURCE,
    INFER_MULTILINE_SOURCE,
    INFER_NESTED_SOURCE,
    SOURCE,
    runner,
    write_text_file,
)


def test_route_infer_from_line_extracts_inferred_full_route_as_json(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "infer_nested.c", INFER_NESTED_SOURCE)

    result = runner.invoke(
        app,
        ["route", "InferNested", str(source), "--infer-from-line", "7", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["results"][0]["routes"] == ["case[STS_IDLE]/while[sts > 0]/if[sts == 1]"]
    assert any(line["text"] == "                Work();" for line in payload["results"][0]["rendered_lines"])


def test_route_infer_from_line_uses_header_line_of_nested_branch(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "infer_nested.c", INFER_NESTED_SOURCE)

    result = runner.invoke(
        app,
        ["route", "InferNested", str(source), "--infer-from-line", "6", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["results"][0]["routes"] == ["case[STS_IDLE]/while[sts > 0]/if[sts == 1]"]
    assert any(line["text"] == "            if (sts == 1) {" for line in payload["results"][0]["rendered_lines"])


def test_route_infer_from_line_supports_multiline_condition_expression(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "infer_multiline.c", INFER_MULTILINE_SOURCE)

    result = runner.invoke(
        app,
        ["route", "InferMultiline", str(source), "--infer-from-line", "7", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["results"][0]["routes"] == ["while[value > 0]/if[value == 1]"]


def test_route_infer_from_line_can_infer_existing_nested_case_else_if_path(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)

    result = runner.invoke(
        app,
        ["route", "FooFunction", str(source), "--infer-from-line", "17", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["results"][0]["routes"] == ["case[CMD_HOGE]/else-if[errno == EINT]"]


def test_route_infer_from_line_fails_for_line_outside_any_branch(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "else_route.c", ELSE_SOURCE)

    result = runner.invoke(
        app,
        ["route", "ElseRoute", str(source), "--infer-from-line", "9"],
    )

    assert result.exit_code == 1
    assert "branch route を特定できません" in result.output


def test_route_infer_from_line_fails_for_ambiguous_line(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "ambiguous_line.c", AMBIGUOUS_LINE_ROUTE_SOURCE)

    result = runner.invoke(
        app,
        ["route", "AmbiguousLine", str(source), "--infer-from-line", "3"],
    )

    assert result.exit_code == 1
    assert "一意に決まりません" in result.output


def test_route_infer_from_line_rejects_route_combination(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "else_route.c", ELSE_SOURCE)

    result = runner.invoke(
        app,
        ["route", "ElseRoute", str(source), "--route", "else", "--infer-from-line", "6"],
    )

    assert result.exit_code == 1
    assert "--route と --infer-from-line は併用できません" in result.output


def test_route_infer_from_line_rejects_multiple_input_files(tmp_path: Path) -> None:
    first = write_text_file(tmp_path, "one.c", ELSE_SOURCE)
    second = write_text_file(tmp_path, "two.c", ELSE_SOURCE)

    result = runner.invoke(
        app,
        ["route", "ElseRoute", str(first), str(second), "--infer-from-line", "6"],
    )

    assert result.exit_code == 1
    assert "単一 input file" in result.output


def test_route_infer_from_line_fails_when_line_is_not_in_target_function(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)

    result = runner.invoke(
        app,
        ["route", "FooFunction", str(source), "--infer-from-line", "1"],
    )

    assert result.exit_code == 1
    assert "行 1 を含む関数が見つかりません" in result.output


def test_route_infer_from_line_fails_when_multiple_functions_match_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = write_text_file(
        tmp_path,
        "repeat.c",
        "int Repeat(void)\n{\n    if (1) {\n        return 1;\n    }\n}\n",
    )
    original_find_functions = run_module.find_functions

    def _duplicate_matches(parsed: ParsedSource, name: str) -> tuple[Node, ...]:
        matches = original_find_functions(parsed, name)
        return matches + matches

    monkeypatch.setattr(run_module, "find_functions", _duplicate_matches)

    with pytest.raises(CiftError, match="複数見つかりました"):
        run_module.run_route(
            "Repeat",
            inputs=(source,),
            defines=[],
            language="auto",
            routes=(),
            infer_from_line=3,
        )
