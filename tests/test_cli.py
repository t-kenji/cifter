from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cifter.cli import app
from tests.support import (
    CPP_MEMBER_SOURCE,
    CPP_TEMPLATE_SOURCE,
    EXPECTED_VERSION,
    HEADER_CPP_SOURCE,
    SOURCE,
    runner,
    write_text_file,
)


def test_function_extracts_full_implementation(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "--name", "FooFunction", "--source", str(source)])
    assert result.exit_code == 0
    assert "4: int FooFunction(int command)" in result.stdout
    assert "28:     return -9;" in result.stdout


def test_help_lists_language_option_for_all_subcommands() -> None:
    for command in ("function", "flow", "path"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0
        assert "--language" in result.stdout


def test_cli_language_option_overrides_header_detection(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "header_cpp.h", HEADER_CPP_SOURCE)
    result = runner.invoke(
        app,
        ["function", "--name", "HeaderCpp", "--source", str(source), "--language", "cpp"],
    )

    assert result.exit_code == 0
    assert "2: inline int HeaderCpp(int &value)" in result.stdout
    assert result.stderr == ""


def test_cpp_function_extracts_out_of_line_method(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "worker.cpp", CPP_MEMBER_SOURCE)
    result = runner.invoke(app, ["function", "--name", "Step", "--source", str(source)])

    assert result.exit_code == 0
    assert "7: int Worker::Step(int *ptr)" in result.stdout
    assert "15:     return 1;" in result.stdout


def test_cpp_function_extracts_template_definition(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "template.hpp", CPP_TEMPLATE_SOURCE)
    result = runner.invoke(app, ["function", "--name", "Pick", "--source", str(source)])

    assert result.exit_code == 0
    assert "1: template <typename T>" in result.stdout
    assert "4:     return value;" in result.stdout


def test_missing_function_fails(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "--name", "Missing", "--source", str(source)])
    assert result.exit_code == 1
    assert "関数が見つかりません" in result.stderr


def test_cli_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "function" in result.stdout
    assert "flow" in result.stdout
    assert "path" in result.stdout


def test_subcommand_help_lists_color_options() -> None:
    for command in ("function", "flow", "path"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0
        assert "--color" in result.stdout
        assert "--no-color" in result.stdout


def test_flow_help_lists_highlight_option_only_for_flow() -> None:
    flow_result = runner.invoke(app, ["flow", "--help"])
    function_result = runner.invoke(app, ["function", "--help"])
    path_result = runner.invoke(app, ["path", "--help"])

    assert flow_result.exit_code == 0
    assert function_result.exit_code == 0
    assert path_result.exit_code == 0
    assert "--highlight" in flow_result.stdout
    assert "--highlight" not in function_result.stdout
    assert "--highlight" not in path_result.stdout


def test_cli_version_prints_project_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == EXPECTED_VERSION


def test_python_module_execution(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = subprocess.run(
        [sys.executable, "-m", "cifter", "function", "--name", "FooFunction", "--source", str(source)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "4: int FooFunction(int command)" in result.stdout


def test_python_module_version() -> None:
    result = subprocess.run([sys.executable, "-m", "cifter", "--version"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert result.stdout.strip() == EXPECTED_VERSION
