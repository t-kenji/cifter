from __future__ import annotations

from pathlib import Path

from cifter.cli import app
from cifter.extract_flow import extract_flow
from cifter.model import TrackPath
from cifter.parser import parse_source
from tests.support import (
    BLOCK_CASE_SOURCE,
    CPP_MEMBER_SOURCE,
    MULTILINE_TRACK_SOURCE,
    SOURCE,
    TRACK_SOURCE,
    runner,
    write_text_file,
)


def test_flow_keeps_skeleton_and_track_lines(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(
        app,
        [
            "flow",
            "--function",
            "FooFunction",
            "--source",
            str(source),
            "--track",
            "state",
            "--track",
            "ctx->state",
        ],
    )
    assert result.exit_code == 0
    assert "9:     switch (command) {" in result.stdout
    assert "11:         state = RUN;" in result.stdout
    assert "13:         if (ret == OK) {" in result.stdout
    assert "16:         } else if (errno == EINT) {" in result.stdout
    assert "25:         break;" in result.stdout


def test_flow_renders_ellipsis_for_omitted_regions(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
    result = runner.invoke(
        app,
        [
            "flow",
            "--function",
            "TrackOnly",
            "--source",
            str(source),
            "--track",
            "state",
        ],
    )
    assert result.exit_code == 0
    assert result.stdout == (
        " 5: int TrackOnly(Context *ctx)\n"
        " 6: {\n"
        " 7:     int state = 0;\n"
        "        ...\n"
        " 9:     state = state + 1;\n"
        "10:     return state;\n"
        "11: }\n"
    )


def test_flow_keeps_break_inside_case_block(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "block_case.c", BLOCK_CASE_SOURCE)
    result = runner.invoke(
        app,
        [
            "flow",
            "--function",
            "BlockCaseRoute",
            "--source",
            str(source),
        ],
    )
    assert result.exit_code == 0
    assert "4:     case REQ_A:" in result.stdout
    assert "5:     {" in result.stdout
    assert "7:         if (x > 0) {" in result.stdout
    assert "11:         break;" in result.stdout
    assert "12:     }" in result.stdout
    assert "13:     default:" in result.stdout
    assert "14:     {" in result.stdout
    assert "15:         break;" in result.stdout
    assert "16:     }" in result.stdout


def test_flow_track_requires_exact_match(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
    result = runner.invoke(
        app,
        [
            "flow",
            "--function",
            "TrackOnly",
            "--source",
            str(source),
            "--track",
            "state",
        ],
    )
    assert result.exit_code == 0
    assert "int state = 0;" in result.stdout
    assert "state = state + 1;" in result.stdout
    assert "ctx->state = 1;" not in result.stdout


def test_flow_track_keeps_matching_access_path(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
    result = runner.invoke(
        app,
        [
            "flow",
            "--function",
            "TrackOnly",
            "--source",
            str(source),
            "--track",
            "ctx->state",
        ],
    )
    assert result.exit_code == 0
    assert "ctx->state = 1;" in result.stdout
    assert "int state = 0;" not in result.stdout


def test_extract_flow_records_track_highlights_for_matching_identifiers(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
    parsed = parse_source(source, [])
    result = extract_flow(parsed, "TrackOnly", (TrackPath.parse("state"),), include_highlights=True)

    declaration_line = next(line for line in result.lines if line.text == "    int state = 0;")
    assignment_line = next(line for line in result.lines if line.text == "    state = state + 1;")
    return_line = next(line for line in result.lines if line.text == "    return state;")

    assert [(span.start_column, span.end_column, span.kind) for span in declaration_line.highlights] == [
        (8, 13, "track_match")
    ]
    assert [(span.start_column, span.end_column, span.kind) for span in assignment_line.highlights] == [
        (4, 9, "track_match"),
        (12, 17, "track_match"),
    ]
    assert [(span.start_column, span.end_column, span.kind) for span in return_line.highlights] == [
        (11, 16, "track_match")
    ]


def test_extract_flow_records_track_highlights_for_multiline_field_expression(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "multiline_track.c", MULTILINE_TRACK_SOURCE)
    parsed = parse_source(source, [])
    result = extract_flow(parsed, "TrackMultiline", (TrackPath.parse("ctx->state"),), include_highlights=True)

    first_line = next(line for line in result.lines if line.text == "    ctx")
    second_line = next(line for line in result.lines if line.text == "        ->state = 1;")
    return_first_line = next(line for line in result.lines if line.text == "    return ctx")
    return_second_line = next(line for line in result.lines if line.text == "        ->state;")

    assert [(span.start_column, span.end_column, span.kind) for span in first_line.highlights] == [
        (4, 7, "track_match")
    ]
    assert [(span.start_column, span.end_column, span.kind) for span in second_line.highlights] == [
        (8, 15, "track_match")
    ]
    assert [(span.start_column, span.end_column, span.kind) for span in return_first_line.highlights] == [
        (11, 14, "track_match")
    ]
    assert [(span.start_column, span.end_column, span.kind) for span in return_second_line.highlights] == [
        (8, 15, "track_match")
    ]


def test_extract_flow_does_not_record_highlights_by_default(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
    parsed = parse_source(source, [])
    result = extract_flow(parsed, "TrackOnly", (TrackPath.parse("state"),))

    assert all(not line.highlights for line in result.lines)


def test_cpp_flow_supports_if_constexpr_and_auto(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "worker.cpp", CPP_MEMBER_SOURCE)
    result = runner.invoke(
        app,
        [
            "flow",
            "--function",
            "Step",
            "--source",
            str(source),
            "--track",
            "current",
        ],
    )

    assert result.exit_code == 0
    assert "9:     auto current = ptr;" in result.stdout
    assert "10:     if constexpr (true) {" in result.stdout
    assert "11:         if (current == nullptr) {" in result.stdout
    assert "15:     return 1;" in result.stdout
