from __future__ import annotations

from pathlib import Path

from cifter.cli import app
from cifter.parser import parse_source
from tests.support import (
    HEADER_C_SOURCE,
    HEADER_CPP_SOURCE,
    runner,
    write_bytes_file,
    write_text_file,
)


def test_parse_source_prefers_c_for_tied_header_quality(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "shared.h", HEADER_C_SOURCE)
    parsed = parse_source(source, [])

    assert parsed.resolved_language == "c"
    assert parsed.language_resolution == "quality"
    assert parsed.quality.level == "clean"


def test_parse_source_detects_cpp_header_by_quality(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "header_cpp.h", HEADER_CPP_SOURCE)
    parsed = parse_source(source, [])

    assert parsed.resolved_language == "cpp"
    assert parsed.language_resolution == "quality"


def test_quality_diagnostics_report_crlf_normalization(tmp_path: Path) -> None:
    source = write_bytes_file(tmp_path, "crlf.c", b"int CrLf(void)\r\n{\r\n    return 1;\r\n}\r\n")
    result = runner.invoke(app, ["function", "--name", "CrLf", "--source", str(source)])

    assert result.exit_code == 0
    assert "1: int CrLf(void)" in result.stdout
    assert "quality[input]:" in result.stderr
    assert "CRLF" in result.stderr


def test_quality_diagnostics_report_bom_normalization(tmp_path: Path) -> None:
    source = write_bytes_file(tmp_path, "bom.c", b"\xef\xbb\xbfint Bommed(void)\n{\n    return 1;\n}\n")
    result = runner.invoke(app, ["function", "--name", "Bommed", "--source", str(source)])

    assert result.exit_code == 0
    assert "1: int Bommed(void)" in result.stdout
    assert "quality[input]:" in result.stderr
    assert "BOM" in result.stderr


def test_non_utf8_input_fails(tmp_path: Path) -> None:
    source = write_bytes_file(
        tmp_path,
        "non_utf8.c",
        "int Bad(void)\n{\n    // あ\n    return 1;\n}\n".encode("cp932"),
    )
    result = runner.invoke(app, ["function", "--name", "Bad", "--source", str(source)])

    assert result.exit_code == 1
    assert "UTF-8" in result.stderr
