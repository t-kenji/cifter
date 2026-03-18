from __future__ import annotations

from pathlib import Path

from cifter.cli import app
from cifter.parser import parse_source
from tests.support import (
    PREPROCESS_DEFINE_EXPR_SOURCE,
    PREPROCESS_ERROR_DIRECTIVE_SOURCE,
    PREPROCESS_FUNCTION_MACRO_SOURCE,
    PREPROCESS_MULTILINE_DEFINE_SOURCE,
    PREPROCESS_MULTILINE_IF_SOURCE,
    PREPROCESS_NESTED_SOURCE,
    PREPROCESS_SOURCE,
    PREPROCESS_TAB_DEFINE_SOURCE,
    PREPROCESS_TAB_DIRECTIVE_SOURCE,
    PREPROCESS_UNSUPPORTED_DIRECTIVE_SOURCE,
    runner,
    write_text_file,
)


def test_preprocessor_uses_d_and_preserves_line_numbers(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "flag.c", PREPROCESS_SOURCE)
    result = runner.invoke(
        app,
        ["function", "--name", "Flagged", "--source", str(source), "-D", "DEF_FOO", "-D", "ENABLE_BAR=1"],
    )
    assert result.exit_code == 0
    assert "4:     return 1;" in result.stdout
    assert "10:     return 2;" not in result.stdout
    assert "12:     return 3;" in result.stdout


def test_preprocessor_handles_nested_define_and_undef(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "nested.c", PREPROCESS_NESTED_SOURCE)
    result = runner.invoke(app, ["function", "--name", "Nested", "--source", str(source), "-D", "OUTER"])
    assert result.exit_code == 0
    assert "6:     return 1;" in result.stdout
    assert "8:     return 2;" not in result.stdout
    assert "13:     return 3;" not in result.stdout
    assert "15:     return 4;" in result.stdout


def test_preprocessor_handles_tabbed_else_and_endif_comments(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "tabbed.c", PREPROCESS_TAB_DIRECTIVE_SOURCE)
    result = runner.invoke(app, ["function", "--name", "Tabbed", "--source", str(source), "-D", "ENABLE_FIRST"])
    assert result.exit_code == 0
    assert "4:     return 1;" in result.stdout
    assert "6:     return 0;" not in result.stdout
    assert "8:     return 9;" in result.stdout


def test_preprocessor_handles_tabbed_define_and_undef(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "tab_macros.c", PREPROCESS_TAB_DEFINE_SOURCE)
    result = runner.invoke(app, ["function", "--name", "TabMacros", "--source", str(source)])
    assert result.exit_code == 0
    assert "5:     return 1;" in result.stdout
    assert "9:     return 2;" in result.stdout
    assert "11:     return 3;" in result.stdout


def test_preprocessor_handles_multiline_if_conditions(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "multi_if.c", PREPROCESS_MULTILINE_IF_SOURCE)
    result = runner.invoke(app, ["function", "--name", "MultiIf", "--source", str(source), "-D", "ENABLE_B"])
    assert result.exit_code == 0
    assert "5:     return 1;" in result.stdout
    assert "6:     return 0;" not in result.stdout


def test_preprocessor_handles_multiline_define_and_undef(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "multi_define.c", PREPROCESS_MULTILINE_DEFINE_SOURCE)
    result = runner.invoke(app, ["function", "--name", "MultiDefine", "--source", str(source)])
    assert result.exit_code == 0
    assert "6:     return 1;" in result.stdout
    assert "9:     return 2;" not in result.stdout
    assert "12:     return 3;" in result.stdout


def test_preprocessor_handles_define_with_equality_expression(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "define_expr.c", PREPROCESS_DEFINE_EXPR_SOURCE)
    result = runner.invoke(app, ["function", "--name", "DefineExpr", "--source", str(source)])
    assert result.exit_code == 0
    assert "5:     return 1;" in result.stdout
    assert "7:     return 2;" not in result.stdout


def test_preprocessor_handles_function_like_macro_conditions(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "function_macro.c", PREPROCESS_FUNCTION_MACRO_SOURCE)
    result = runner.invoke(app, ["function", "--name", "FunctionMacro", "--source", str(source)])
    assert result.exit_code == 0
    assert "5:     return 1;" in result.stdout
    assert "7:     return 2;" not in result.stdout


def test_parse_source_does_not_warn_for_active_pragma(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "pragma.c", PREPROCESS_UNSUPPORTED_DIRECTIVE_SOURCE)
    parsed = parse_source(source, [], "c")
    assert parsed.quality.level == "clean"


def test_parse_source_does_not_warn_for_active_error_directive(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "error.c", PREPROCESS_ERROR_DIRECTIVE_SOURCE)
    parsed = parse_source(source, [], "c")
    assert parsed.quality.level == "clean"


def test_cli_keeps_pragma_without_preprocess_warning(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "pragma.c", PREPROCESS_UNSUPPORTED_DIRECTIVE_SOURCE)
    result = runner.invoke(app, ["function", "--name", "KeepPragma", "--source", str(source)])
    assert result.exit_code == 0
    assert "2: int KeepPragma(void)" in result.stdout
    assert "quality[preprocess]:" not in result.stderr


def test_cli_keeps_error_directive_without_preprocess_warning(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "error.c", PREPROCESS_ERROR_DIRECTIVE_SOURCE)
    result = runner.invoke(app, ["function", "--name", "KeepError", "--source", str(source)])
    assert result.exit_code == 0
    assert "2: int KeepError(void)" in result.stdout
    assert "quality[preprocess]:" not in result.stderr
