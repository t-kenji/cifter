from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cifter
from cifter.cli import app
from tests.support import EXPECTED_VERSION, normalize_help_output, runner, write_text_file


def test_cli_help_lists_v1_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    help_text = normalize_help_output(result.stdout)
    assert "function" in help_text
    assert "flow" in help_text
    assert "route" in help_text
    assert "関数実装全体を切り出す" in help_text
    assert "指定 route DSL に沿う枝だけを切り出す" in help_text
    assert "install-completion" not in help_text


def test_function_help_uses_positional_symbol_and_inputs() -> None:
    result = runner.invoke(app, ["function", "--help"])

    assert result.exit_code == 0
    help_text = normalize_help_output(result.stdout)
    assert "SYMBOL" in help_text
    assert "INPUTS" in help_text
    assert "--files-from" in help_text
    assert "--format" in help_text
    assert "--strict-inputs" in help_text


def test_route_help_is_exposed_instead_of_path() -> None:
    route_result = runner.invoke(app, ["route", "--help"])
    path_result = runner.invoke(app, ["path", "--help"])

    assert route_result.exit_code == 0
    assert path_result.exit_code == 2
    route_help = normalize_help_output(route_result.stdout)
    assert "--route" in route_help
    assert "--infer-from-line" in route_help


def test_cli_version_prints_project_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == EXPECTED_VERSION


def test_python_module_execution_supports_v1_positional_cli(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", "int FooFunction(void)\n{\n    return 1;\n}\n")
    result = subprocess.run(
        [sys.executable, "-m", "cifter", "function", "FooFunction", str(source)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "1: int FooFunction(void)" in result.stdout


def test_import_cifter_does_not_export_cli_main() -> None:
    assert hasattr(cifter, "__version__")
    assert not hasattr(cifter, "main")
