from __future__ import annotations

import json
from pathlib import Path

from cifter.cli import app
from tests.support import (
    DUPLICATE_FUNCTION_SOURCE,
    ELSE_SOURCE,
    SOURCE,
    normalize_help_output,
    runner,
    write_bytes_file,
    write_text_file,
)


def test_function_extracts_full_implementation_with_positional_args(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "FooFunction", str(source), "--format", "text"])

    assert result.exit_code == 0
    assert "4: int FooFunction(int command)" in result.stdout
    assert "28:     return -9;" in result.stdout


def test_flow_outputs_json_for_non_tty_and_keeps_track_lines(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["flow", "FooFunction", str(source), "--track", "state", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "flow"
    rendered_lines = payload["results"][0]["rendered_lines"]
    texts = [line["text"] for line in rendered_lines]
    assert "    switch (command) {" in texts
    assert "        state = RUN;" in texts
    assert "        } else if (errno == EINT) {" in texts


def test_route_replaces_path_and_extracts_selected_branch(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "else_route.c", ELSE_SOURCE)
    result = runner.invoke(
        app,
        ["route", "ElseRoute", str(source), "--route", "else", "--format", "text"],
    )

    assert result.exit_code == 0
    assert "3:     if (x > 0) {" in result.stdout
    assert "5:     } else {" in result.stdout
    assert "6:         WorkB();" in result.stdout
    assert "WorkA();" not in result.stdout


def test_directory_input_and_files_from_return_same_single_result(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    files_from = write_text_file(tmp_path, "targets.txt", f"{source}\n")

    dir_result = runner.invoke(app, ["function", "FooFunction", str(tmp_path), "--format", "json"])
    files_result = runner.invoke(
        app,
        ["function", "FooFunction", "--files-from", str(files_from), "--format", "json"],
    )

    assert dir_result.exit_code == 0
    assert files_result.exit_code == 0
    assert len(json.loads(dir_result.stdout)["results"]) == 1
    assert len(json.loads(files_result.stdout)["results"]) == 1


def test_duplicate_inputs_are_deduplicated(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    files_from = write_text_file(tmp_path, "targets.txt", f"{source}\n")
    result = runner.invoke(
        app,
        [
            "function",
            "FooFunction",
            str(source),
            "--files-from",
            str(files_from),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert len(json.loads(result.stdout)["results"]) == 1


def test_run_skips_missing_inputs_by_default(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    missing = write_text_file(tmp_path, "missing.c", "int Other(void)\n{\n    return 0;\n}\n")
    result = runner.invoke(
        app,
        ["function", "FooFunction", str(source), str(missing), "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["results"]) == 1
    assert payload["diagnostics"][0]["code"] == "function_not_found"
    assert payload["diagnostics"][0]["severity"] == "warning"


def test_run_strict_inputs_fails_when_any_input_is_missing_target_symbol(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    missing = write_text_file(tmp_path, "missing.c", "int Other(void)\n{\n    return 0;\n}\n")
    result = runner.invoke(
        app,
        ["function", "FooFunction", str(source), str(missing), "--strict-inputs", "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert len(payload["results"]) == 1
    assert payload["diagnostics"][0]["code"] == "function_not_found"
    assert payload["diagnostics"][0]["severity"] == "error"


def test_route_requires_route_option(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["route", "FooFunction", str(source)])

    assert result.exit_code == 2
    normalized = normalize_help_output(result.output)
    assert "--route" in normalized


def test_files_from_stdin_matches_direct_input(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    direct_result = runner.invoke(app, ["function", "FooFunction", str(source), "--format", "json"])
    stdin_result = runner.invoke(
        app,
        ["function", "FooFunction", "--files-from", "-", "--format", "json"],
        input=f"{source}\n",
    )

    assert direct_result.exit_code == 0
    assert stdin_result.exit_code == 0
    assert json.loads(direct_result.stdout)["results"] == json.loads(stdin_result.stdout)["results"]


def test_non_utf8_files_from_fails_with_user_facing_message(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    files_from = write_bytes_file(tmp_path, "targets.txt", b"\x82\xa0\n" + f"{source}\n".encode())
    result = runner.invoke(app, ["function", "FooFunction", "--files-from", str(files_from)])

    assert result.exit_code == 1
    assert "--files-from" in result.output
    assert "UTF-8" in result.output


def test_same_file_multiple_matches_return_source_order(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "duplicate.c", DUPLICATE_FUNCTION_SOURCE)
    result = runner.invoke(app, ["function", "Repeat", str(source), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [item["span"]["start_line"] for item in payload["results"]] == [1, 6]


def test_run_fails_when_no_inputs_match_target_symbol(tmp_path: Path) -> None:
    missing = write_text_file(tmp_path, "missing.c", "int Other(void)\n{\n    return 0;\n}\n")
    result = runner.invoke(app, ["function", "FooFunction", str(missing), "--format", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["results"] == []
    assert payload["diagnostics"][-1]["code"] == "no_results"
