from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from cifter import cli as cli_module
from cifter.cli import app
from cifter.render_text import _rendered_column_for_source_column, should_use_color
from cifter.run import resolve_input_files, run_function
from tests.support import (
    ANSI_ESCAPE_PATTERN,
    ELSE_SOURCE,
    TRACK_SOURCE,
    FakeStream,
    runner,
    strip_ansi,
    write_text_file,
)


def test_flow_json_includes_highlights_only_when_highlight_flag_is_set(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
    plain = runner.invoke(app, ["flow", "TrackOnly", str(source), "--track", "state", "--format", "json"])
    highlighted = runner.invoke(
        app,
        ["flow", "TrackOnly", str(source), "--track", "state", "--highlight", "--format", "json"],
    )

    assert plain.exit_code == 0
    assert highlighted.exit_code == 0
    plain_lines = json.loads(plain.stdout)["results"][0]["rendered_lines"]
    highlighted_lines = json.loads(highlighted.stdout)["results"][0]["rendered_lines"]
    assert all(not line["highlights"] for line in plain_lines)
    assert any(line["highlights"] for line in highlighted_lines)


def test_text_output_can_be_colored(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
    result = runner.invoke(app, ["flow", "TrackOnly", str(source), "--track", "state", "--highlight", "--color"])

    assert result.exit_code == 0
    assert ANSI_ESCAPE_PATTERN.search(result.stdout) is not None
    assert "7:     int state = 0;" in strip_ansi(result.stdout)


def test_rendered_column_for_source_column_expands_tabs() -> None:
    assert _rendered_column_for_source_column("\t\tst->spl.status = status;", 2) == 8


def test_should_use_color_prefers_explicit_value_over_tty() -> None:
    assert should_use_color(True, FakeStream(is_tty=False)) is True
    assert should_use_color(False, FakeStream(is_tty=True)) is False


def test_multiple_result_text_header_includes_command_symbol_route_and_span(tmp_path: Path) -> None:
    first = write_text_file(tmp_path, "one.c", ELSE_SOURCE)
    second = write_text_file(tmp_path, "two.c", ELSE_SOURCE)
    result = runner.invoke(
        app,
        ["route", "ElseRoute", str(first), str(second), "--route", "else", "--format", "text"],
    )

    assert result.exit_code == 0
    assert f"file: {first}" in result.stdout
    assert "command=route symbol=ElseRoute route=else" in result.stdout
    assert "[1-11]" in result.stdout


def test_auto_format_uses_json_for_non_tty_and_text_for_tty(tmp_path: Path, monkeypatch) -> None:
    source = write_text_file(tmp_path, "foo.c", "int FooFunction(void)\n{\n    return 1;\n}\n")
    resolved_inputs = resolve_input_files([source], files_from=[])
    run_result = run_function("FooFunction", inputs=resolved_inputs, defines=[], language="auto")

    class Capture(StringIO):
        def __init__(self, *, is_tty: bool) -> None:
            super().__init__()
            self._is_tty = is_tty

        def isatty(self) -> bool:
            return self._is_tty

    non_tty = Capture(is_tty=False)
    monkeypatch.setattr(cli_module.sys, "stdout", non_tty)
    cli_module._write_run_result(run_result, format_mode="auto", color=None)
    assert json.loads(non_tty.getvalue())["command"] == "function"

    tty = Capture(is_tty=True)
    monkeypatch.setattr(cli_module.sys, "stdout", tty)
    cli_module._write_run_result(run_result, format_mode="auto", color=None)
    assert "1: int FooFunction(void)" in strip_ansi(tty.getvalue())


def test_auto_format_with_explicit_color_forces_text(tmp_path: Path, monkeypatch) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
    resolved_inputs = resolve_input_files([source], files_from=[])
    run_result = run_function("TrackOnly", inputs=resolved_inputs, defines=[], language="auto")

    class Capture(StringIO):
        def isatty(self) -> bool:
            return False

    output = Capture()
    monkeypatch.setattr(cli_module.sys, "stdout", output)
    cli_module._write_run_result(run_result, format_mode="auto", color=True)
    assert "7:     int state = 0;" in strip_ansi(output.getvalue())
    assert output.getvalue().lstrip().startswith("{") is False
