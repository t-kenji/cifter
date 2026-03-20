from __future__ import annotations

import json
from pathlib import Path

from cifter.cli import app
from cifter.parser import parse_source
from tests.support import (
    HEADER_C_SOURCE,
    HEADER_CPP_SOURCE,
    PREPROCESS_SOURCE,
    runner,
    write_bytes_file,
    write_text_file,
)


def test_parse_source_prefers_c_for_tied_header_quality(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "shared.h", HEADER_C_SOURCE)
    parsed = parse_source(source, [])

    assert parsed.resolved_language == "c"
    assert parsed.language_resolution == "quality"


def test_parse_source_detects_cpp_header_by_quality(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "header_cpp.h", HEADER_CPP_SOURCE)
    parsed = parse_source(source, [])

    assert parsed.resolved_language == "cpp"
    assert parsed.language_resolution == "quality"


def test_function_json_embeds_input_normalization_diagnostics(tmp_path: Path) -> None:
    source = write_bytes_file(tmp_path, "crlf.c", b"int CrLf(void)\r\n{\r\n    return 1;\r\n}\r\n")
    result = runner.invoke(app, ["function", "CrLf", str(source), "--format", "json"])

    assert result.exit_code == 0
    diagnostics = json.loads(result.stdout)["results"][0]["diagnostics"]
    assert any(item["category"] == "input" for item in diagnostics)


def test_non_utf8_input_fails(tmp_path: Path) -> None:
    source = write_bytes_file(
        tmp_path,
        "non_utf8.c",
        "int Bad(void)\n{\n    // あ\n    return 1;\n}\n".encode("cp932"),
    )
    result = runner.invoke(app, ["function", "Bad", str(source)])

    assert result.exit_code == 1
    assert "UTF-8" in result.output


def test_preprocessor_uses_define_with_v1_cli(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "flag.c", PREPROCESS_SOURCE)
    result = runner.invoke(
        app,
        ["function", "Flagged", str(source), "-D", "DEF_FOO", "-D", "ENABLE_BAR=1", "--format", "text"],
    )

    assert result.exit_code == 0
    assert "4:     return 1;" in result.stdout
    assert "10:     return 2;" not in result.stdout
    assert "12:     return 3;" in result.stdout
