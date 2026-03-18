from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from io import StringIO
from pathlib import Path

from typer.testing import CliRunner

from cifter.cli import app
from cifter.extract_flow import extract_flow
from cifter.model import ExtractedLine, ExtractionResult, InlineHighlightSpan, SourceSpan, TrackPath
from cifter.parser import parse_source
from cifter.render import _rendered_column_for_source_column, _should_use_color, print_result


def _read_expected_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    assert isinstance(version, str)
    return f"cift {version}"


runner = CliRunner()
EXPECTED_VERSION = _read_expected_version()


SOURCE = """#define LOCAL_FLAG 1
#include <stdio.h>

int FooFunction(int command)
{
    int state = INIT;
    int ret = NG;

    switch (command) {
    case CMD_HOGE:
        state = RUN;
        ret = DoHoge(state);
        if (ret == OK) {
            state = DONE;
            return state;
        } else if (errno == EINT) {
            state = RETRY;
            return -2;
        } else {
            state = ERR;
            return -1;
        }

    default:
        break;
    }

    return -9;
}

int OtherFunction(void)
{
    return 0;
}
"""


TRACK_SOURCE = """typedef struct Context {
    int state;
} Context;

int TrackOnly(Context *ctx)
{
    int state = 0;
    ctx->state = 1;
    state = state + 1;
    return state;
}
"""


MULTILINE_TRACK_SOURCE = """typedef struct Context {
    int state;
} Context;

int TrackMultiline(Context *ctx)
{
    ctx
        ->state = 1;
    return ctx
        ->state;
}
"""


TAB_TRACK_SOURCE = """int TabTrack(void)
{
\t\tst->spl.status = status;
    return 0;
}
"""


PATH_TRAILING_SOURCE = """int RouteTail(int x)
{
    switch (x) {
    case 1:
        Prep();
        if (x > 0) {
            Work();
        }
        After();
        break;
    default:
        break;
    }
}
"""


ELSE_SOURCE = """int ElseRoute(int x)
{
    if (x > 0) {
        WorkA();
    } else {
        WorkB();
    }

    After();
    return 3;
}
"""


DEFAULT_SOURCE = """int DefaultRoute(int x)
{
    switch (x) {
    case 1:
        return 1;
    default:
        HandleDefault();
        break;
    }
}
"""


BLOCK_CASE_SOURCE = """int BlockCaseRoute(int x)
{
    switch (x) {
    case REQ_A:
    {
        Prep();
        if (x > 0) {
            Work();
        }
        After();
        break;
    }
    default:
    {
        break;
    }
    }
}
"""


AMBIGUOUS_SOURCE = """int Ambiguous(int x)
{
    if (x > 0) {
        First();
    }

    if (x > 0) {
        Second();
    }
}
"""


LOOP_PATH_SOURCE = """int LoopRoute(int sts)
{
    if (status == BAR) {
    } else {
        if (POWER == ON) {
        } else {
        }
        for (;;) {
            if (result == OK) {
            } else {
            }
            if (res == NG) break;
            switch (sts) {
            case STS_IDLE:
                Work();
                break;
            }
        }
    }
}
"""


WHILE_ROUTE_SOURCE = """int WhileRoute(int sts)
{
    while ((sts > 0)) {
        switch (sts) {
        case STS_IDLE:
            Work();
            break;
        }
    }
}
"""


DO_WHILE_ROUTE_SOURCE = """int DoWhileRoute(int sts)
{
    do {
        switch (sts) {
        case STS_IDLE:
            Work();
            break;
        }
    } while ((sts > 0));
}
"""


AMBIGUOUS_FOR_SOURCE = """int AmbiguousFor(void)
{
    for (;;) {
        First();
    }

    for (;;) {
        Second();
    }
}
"""


PREPROCESS_SOURCE = """int Flagged(void)
{
#if defined(DEF_FOO)
    return 1;
#else
    return 0;
#endif
#ifdef LOCAL_FLAG
    return 2;
#endif
#if ENABLE_BAR == 1
    return 3;
#endif
}
"""


PREPROCESS_NESTED_SOURCE = """int Nested(void)
{
#define LOCAL 1
#if defined(LOCAL)
#if defined(OUTER)
    return 1;
#else
    return 2;
#endif
#endif
#undef LOCAL
#ifdef LOCAL
    return 3;
#endif
    return 4;
}
"""


PREPROCESS_TAB_DIRECTIVE_SOURCE = """int Tabbed(void)
{
#if defined(ENABLE_FIRST)
    return 1;
#else\t// fallback
    return 0;
#endif\t// end first
    return 9;
}
"""


PREPROCESS_TAB_DEFINE_SOURCE = """int TabMacros(void)
{
#define\tLOCAL 1
#ifdef\tLOCAL
    return 1;
#endif\t// local
#undef\tLOCAL
#ifndef\tLOCAL
    return 2;
#endif\t// after undef
    return 3;
}
"""


PREPROCESS_MULTILINE_IF_SOURCE = """int MultiIf(void)
{
#if defined(ENABLE_A) || \\
    defined(ENABLE_B)
    return 1;
#else
    return 0;
#endif
}
"""


PREPROCESS_MULTILINE_DEFINE_SOURCE = """int MultiDefine(void)
{
#define LOCAL_FLAG \\
    1
#ifdef LOCAL_FLAG
    return 1;
#endif
#undef LOCAL_FLAG
#ifdef LOCAL_FLAG
    return 2;
#endif
    return 3;
}
"""


PREPROCESS_UNSUPPORTED_DIRECTIVE_SOURCE = """#pragma once
int KeepPragma(void)
{
    return 1;
}
"""


HEADER_C_SOURCE = """int SharedHeader(void)
{
    return 1;
}
"""


HEADER_CPP_SOURCE = """namespace Demo {
inline int HeaderCpp(int &value)
{
    return value;
}
}
"""


CPP_MEMBER_SOURCE = """namespace Demo {
class Worker {
public:
    int Step(int *ptr);
};

int Worker::Step(int *ptr)
{
    auto current = ptr;
    if constexpr (true) {
        if (current == nullptr) {
            return 0;
        }
    }
    return 1;
}
}
"""


CPP_PATH_SOURCE = """namespace Demo {
int Route(int value)
{
    if (value > 0) {
        return 1;
    } else {
        return 0;
    }
}
}
"""


CPP_TEMPLATE_SOURCE = """template <typename T>
T Pick(T value)
{
    return value;
}
"""


ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def test_function_extracts_full_implementation(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "--name", "FooFunction", "--source", str(source)])
    assert result.exit_code == 0
    assert "4: int FooFunction(int command)" in result.stdout
    assert "28:     return -9;" in result.stdout


def test_flow_keeps_skeleton_and_track_lines(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
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
    source = _write(tmp_path, "track.c", TRACK_SOURCE)
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
    source = _write(tmp_path, "block_case.c", BLOCK_CASE_SOURCE)
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
    source = _write(tmp_path, "track.c", TRACK_SOURCE)
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
    source = _write(tmp_path, "track.c", TRACK_SOURCE)
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
    source = _write(tmp_path, "track.c", TRACK_SOURCE)
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
    source = _write(tmp_path, "multiline_track.c", MULTILINE_TRACK_SOURCE)
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
    source = _write(tmp_path, "track.c", TRACK_SOURCE)
    parsed = parse_source(source, [])
    result = extract_flow(parsed, "TrackOnly", (TrackPath.parse("state"),))

    assert all(not line.highlights for line in result.lines)


def test_flow_color_output_does_not_highlight_without_highlight_flag(tmp_path: Path) -> None:
    source = _write(tmp_path, "track.c", TRACK_SOURCE)
    color_result = runner.invoke(
        app,
        ["flow", "--function", "TrackOnly", "--source", str(source), "--track", "state", "--color"],
    )
    plain_result = runner.invoke(
        app,
        ["flow", "--function", "TrackOnly", "--source", str(source), "--track", "state", "--no-color"],
    )

    assert color_result.exit_code == 0
    assert plain_result.exit_code == 0
    assert "48;2;59;130;246" not in color_result.stdout
    assert _strip_ansi(color_result.stdout) == plain_result.stdout


def test_flow_color_output_highlights_track_matches_with_highlight_flag(tmp_path: Path) -> None:
    source = _write(tmp_path, "track.c", TRACK_SOURCE)
    color_result = runner.invoke(
        app,
        [
            "flow",
            "--function",
            "TrackOnly",
            "--source",
            str(source),
            "--track",
            "state",
            "--highlight",
            "--color",
        ],
    )
    plain_result = runner.invoke(
        app,
        ["flow", "--function", "TrackOnly", "--source", str(source), "--track", "state", "--no-color"],
    )

    assert color_result.exit_code == 0
    assert plain_result.exit_code == 0
    assert "48;2;59;130;246" in color_result.stdout
    assert _strip_ansi(color_result.stdout) == plain_result.stdout


def test_flow_highlight_is_noop_without_color_output(tmp_path: Path) -> None:
    source = _write(tmp_path, "track.c", TRACK_SOURCE)
    auto_result = runner.invoke(
        app,
        ["flow", "--function", "TrackOnly", "--source", str(source), "--track", "state", "--highlight"],
    )
    plain_result = runner.invoke(
        app,
        ["flow", "--function", "TrackOnly", "--source", str(source), "--track", "state"],
    )

    assert auto_result.exit_code == 0
    assert plain_result.exit_code == 0
    assert ANSI_ESCAPE_PATTERN.search(auto_result.stdout) is None
    assert auto_result.stdout == plain_result.stdout


def test_rendered_column_for_source_column_expands_tabs() -> None:
    assert _rendered_column_for_source_column("\t\tst->spl.status = status;", 2) == 8
    assert _rendered_column_for_source_column(" \tst->spl.status = status;", 2) == 4


def test_print_result_applies_highlight_after_tab_expansion_and_prefix() -> None:
    result = ExtractionResult(
        span=SourceSpan(file=Path("tab.c"), start_line=12, end_line=12),
        lines=(
            ExtractedLine(
                line_no=12,
                text="\t\tst->spl.status = status;",
                highlights=(InlineHighlightSpan(start_column=2, end_column=16, kind="track_match"),),
            ),
        ),
    )
    output = StringIO()

    print_result(result, "c", color=True, file=output)

    rendered = output.getvalue()
    assert "48;2;59;130;246" in rendered
    assert _strip_ansi(rendered).strip() == "12:         st->spl.status = status;"


def test_path_keeps_selected_case_if_branch_and_following_statements(tmp_path: Path) -> None:
    source = _write(tmp_path, "route_tail.c", PATH_TRAILING_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "RouteTail",
            "--source",
            str(source),
            "--route",
            "case 1 > if x > 0",
        ],
    )
    assert result.exit_code == 0
    assert "4:     case 1:" in result.stdout
    assert "5:         Prep();" in result.stdout
    assert "6:         if (x > 0) {" in result.stdout
    assert "7:             Work();" in result.stdout
    assert "9:         After();" in result.stdout
    assert "10:         break;" in result.stdout
    assert "else" not in result.stdout
    assert "default:" not in result.stdout


def test_path_keeps_parent_if_for_else_if_segment(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "FooFunction",
            "--source",
            str(source),
            "--route",
            "case CMD_HOGE > else if errno == EINT",
        ],
    )
    assert result.exit_code == 0
    assert "13:         if (ret == OK) {" in result.stdout
    assert "16:         } else if (errno == EINT) {" in result.stdout
    assert "18:             return -2;" in result.stdout


def test_path_keeps_parent_if_for_else_segment(tmp_path: Path) -> None:
    source = _write(tmp_path, "else_route.c", ELSE_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "ElseRoute",
            "--source",
            str(source),
            "--route",
            "else",
        ],
    )
    assert result.exit_code == 0
    assert "3:     if (x > 0) {" in result.stdout
    assert "5:     } else {" in result.stdout
    assert "6:         WorkB();" in result.stdout
    assert "9:     After();" in result.stdout
    assert "10:     return 3;" in result.stdout
    assert "WorkA();" not in result.stdout


def test_path_renders_ellipsis_for_omitted_regions(tmp_path: Path) -> None:
    source = _write(tmp_path, "else_route.c", ELSE_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "ElseRoute",
            "--source",
            str(source),
            "--route",
            "else",
        ],
    )
    assert result.exit_code == 0
    assert result.stdout == (
        " 1: int ElseRoute(int x)\n"
        " 2: {\n"
        " 3:     if (x > 0) {\n"
        "            ...\n"
        " 5:     } else {\n"
        " 6:         WorkB();\n"
        " 7:     }\n"
        "        ...\n"
        " 9:     After();\n"
        "10:     return 3;\n"
        "11: }\n"
    )


def test_path_supports_default_route(tmp_path: Path) -> None:
    source = _write(tmp_path, "default_route.c", DEFAULT_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "DefaultRoute",
            "--source",
            str(source),
            "--route",
            "default",
        ],
    )
    assert result.exit_code == 0
    assert "6:     default:" in result.stdout
    assert "7:         HandleDefault();" in result.stdout
    assert "8:         break;" in result.stdout
    assert "case 1" not in result.stdout


def test_path_supports_nested_route_inside_case_block(tmp_path: Path) -> None:
    source = _write(tmp_path, "block_case.c", BLOCK_CASE_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "BlockCaseRoute",
            "--source",
            str(source),
            "--route",
            "case REQ_A > if x > 0",
        ],
    )
    assert result.exit_code == 0
    assert "4:     case REQ_A:" in result.stdout
    assert "5:     {" in result.stdout
    assert "6:         Prep();" in result.stdout
    assert "7:         if (x > 0) {" in result.stdout
    assert "8:             Work();" in result.stdout
    assert "10:         After();" in result.stdout
    assert "11:         break;" in result.stdout
    assert "12:     }" in result.stdout
    assert "default:" not in result.stdout


def test_path_supports_default_route_inside_case_block(tmp_path: Path) -> None:
    source = _write(tmp_path, "block_case.c", BLOCK_CASE_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "BlockCaseRoute",
            "--source",
            str(source),
            "--route",
            "default",
        ],
    )
    assert result.exit_code == 0
    assert "13:     default:" in result.stdout
    assert "14:     {" in result.stdout
    assert "15:         break;" in result.stdout
    assert "16:     }" in result.stdout
    assert "case REQ_A" not in result.stdout


def test_path_supports_loop_segment_before_case_route(tmp_path: Path) -> None:
    source = _write(tmp_path, "loop_route.c", LOOP_PATH_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "LoopRoute",
            "--source",
            str(source),
            "--route",
            "else > for > case STS_IDLE",
        ],
    )
    assert result.exit_code == 0
    assert "3:     if (status == BAR) {" in result.stdout
    assert "4:     } else {" in result.stdout
    assert "8:         for (;;) {" in result.stdout
    assert "13:             switch (sts) {" in result.stdout
    assert "14:             case STS_IDLE:" in result.stdout
    assert "15:                 Work();" in result.stdout
    assert "16:                 break;" in result.stdout
    assert "18:         }" in result.stdout
    assert "POWER == ON" not in result.stdout
    assert "result == OK" not in result.stdout
    assert "res == NG" not in result.stdout


def test_path_supports_while_segment_before_case_route(tmp_path: Path) -> None:
    source = _write(tmp_path, "while_route.c", WHILE_ROUTE_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "WhileRoute",
            "--source",
            str(source),
            "--route",
            "while sts > 0 > case STS_IDLE",
        ],
    )
    assert result.exit_code == 0
    assert "3:     while ((sts > 0)) {" in result.stdout
    assert "4:         switch (sts) {" in result.stdout
    assert "5:         case STS_IDLE:" in result.stdout
    assert "6:             Work();" in result.stdout
    assert "7:             break;" in result.stdout
    assert "8:         }" in result.stdout


def test_path_supports_do_while_segment_before_case_route(tmp_path: Path) -> None:
    source = _write(tmp_path, "do_while_route.c", DO_WHILE_ROUTE_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "DoWhileRoute",
            "--source",
            str(source),
            "--route",
            "do while sts > 0 > case STS_IDLE",
        ],
    )
    assert result.exit_code == 0
    assert "3:     do {" in result.stdout
    assert "4:         switch (sts) {" in result.stdout
    assert "5:         case STS_IDLE:" in result.stdout
    assert "6:             Work();" in result.stdout
    assert "7:             break;" in result.stdout
    assert "8:         }" in result.stdout
    assert "9:     } while ((sts > 0));" in result.stdout


def test_invalid_route_fails(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "FooFunction",
            "--source",
            str(source),
            "--route",
            "case CMD_HOGE > else > if errno == EINT",
        ],
    )
    assert result.exit_code == 1
    assert "else if" in result.stderr


def test_path_does_not_skip_loop_implicitly(tmp_path: Path) -> None:
    source = _write(tmp_path, "loop_route.c", LOOP_PATH_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "LoopRoute",
            "--source",
            str(source),
            "--route",
            "else > case STS_IDLE",
        ],
    )
    assert result.exit_code == 1
    assert "見つかりません" in result.stderr


def test_ambiguous_route_fails(tmp_path: Path) -> None:
    source = _write(tmp_path, "ambiguous.c", AMBIGUOUS_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "Ambiguous",
            "--source",
            str(source),
            "--route",
            "if x > 0",
        ],
    )
    assert result.exit_code == 1
    assert "複数" in result.stderr


def test_ambiguous_for_route_fails(tmp_path: Path) -> None:
    source = _write(tmp_path, "ambiguous_for.c", AMBIGUOUS_FOR_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "AmbiguousFor",
            "--source",
            str(source),
            "--route",
            "for",
        ],
    )
    assert result.exit_code == 1
    assert "複数" in result.stderr


def test_preprocessor_uses_d_and_preserves_line_numbers(tmp_path: Path) -> None:
    source = _write(tmp_path, "flag.c", PREPROCESS_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "Flagged",
            "--source",
            str(source),
            "-D",
            "DEF_FOO",
            "-D",
            "ENABLE_BAR=1",
        ],
    )
    assert result.exit_code == 0
    assert "4:     return 1;" in result.stdout
    assert "10:     return 2;" not in result.stdout
    assert "12:     return 3;" in result.stdout


def test_preprocessor_handles_nested_define_and_undef(tmp_path: Path) -> None:
    source = _write(tmp_path, "nested.c", PREPROCESS_NESTED_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "Nested",
            "--source",
            str(source),
            "-D",
            "OUTER",
        ],
    )
    assert result.exit_code == 0
    assert "6:     return 1;" in result.stdout
    assert "8:     return 2;" not in result.stdout
    assert "13:     return 3;" not in result.stdout
    assert "15:     return 4;" in result.stdout


def test_preprocessor_handles_tabbed_else_and_endif_comments(tmp_path: Path) -> None:
    source = _write(tmp_path, "tabbed.c", PREPROCESS_TAB_DIRECTIVE_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "Tabbed",
            "--source",
            str(source),
            "-D",
            "ENABLE_FIRST",
        ],
    )
    assert result.exit_code == 0
    assert "4:     return 1;" in result.stdout
    assert "6:     return 0;" not in result.stdout
    assert "8:     return 9;" in result.stdout


def test_preprocessor_handles_tabbed_define_and_undef(tmp_path: Path) -> None:
    source = _write(tmp_path, "tab_macros.c", PREPROCESS_TAB_DEFINE_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "TabMacros",
            "--source",
            str(source),
        ],
    )
    assert result.exit_code == 0
    assert "5:     return 1;" in result.stdout
    assert "9:     return 2;" in result.stdout
    assert "11:     return 3;" in result.stdout


def test_preprocessor_handles_multiline_if_conditions(tmp_path: Path) -> None:
    source = _write(tmp_path, "multi_if.c", PREPROCESS_MULTILINE_IF_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "MultiIf",
            "--source",
            str(source),
            "-D",
            "ENABLE_B",
        ],
    )
    assert result.exit_code == 0
    assert "5:     return 1;" in result.stdout
    assert "6:     return 0;" not in result.stdout


def test_preprocessor_handles_multiline_define_and_undef(tmp_path: Path) -> None:
    source = _write(tmp_path, "multi_define.c", PREPROCESS_MULTILINE_DEFINE_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "MultiDefine",
            "--source",
            str(source),
        ],
    )
    assert result.exit_code == 0
    assert "6:     return 1;" in result.stdout
    assert "9:     return 2;" not in result.stdout
    assert "12:     return 3;" in result.stdout


def test_help_lists_language_option_for_all_subcommands() -> None:
    for command in ("function", "flow", "path"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0
        assert "--language" in result.stdout


def test_parse_source_prefers_c_for_tied_header_quality(tmp_path: Path) -> None:
    source = _write(tmp_path, "shared.h", HEADER_C_SOURCE)
    parsed = parse_source(source, [])

    assert parsed.resolved_language == "c"
    assert parsed.language_resolution == "quality"
    assert parsed.quality.level == "clean"


def test_parse_source_detects_cpp_header_by_quality(tmp_path: Path) -> None:
    source = _write(tmp_path, "header_cpp.h", HEADER_CPP_SOURCE)
    parsed = parse_source(source, [])

    assert parsed.resolved_language == "cpp"
    assert parsed.language_resolution == "quality"


def test_cli_language_option_overrides_header_detection(tmp_path: Path) -> None:
    source = _write(tmp_path, "header_cpp.h", HEADER_CPP_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "HeaderCpp",
            "--source",
            str(source),
            "--language",
            "cpp",
        ],
    )

    assert result.exit_code == 0
    assert "2: inline int HeaderCpp(int &value)" in result.stdout
    assert result.stderr == ""


def test_cpp_function_extracts_out_of_line_method(tmp_path: Path) -> None:
    source = _write(tmp_path, "worker.cpp", CPP_MEMBER_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "Step",
            "--source",
            str(source),
        ],
    )

    assert result.exit_code == 0
    assert "7: int Worker::Step(int *ptr)" in result.stdout
    assert "15:     return 1;" in result.stdout


def test_cpp_flow_supports_if_constexpr_and_auto(tmp_path: Path) -> None:
    source = _write(tmp_path, "worker.cpp", CPP_MEMBER_SOURCE)
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


def test_cpp_path_keeps_selected_branch(tmp_path: Path) -> None:
    source = _write(tmp_path, "route.cpp", CPP_PATH_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "Route",
            "--source",
            str(source),
            "--route",
            "if value > 0",
        ],
    )

    assert result.exit_code == 0
    assert "4:     if (value > 0) {" in result.stdout
    assert "5:         return 1;" in result.stdout
    assert "else" not in result.stdout


def test_cpp_function_extracts_template_definition(tmp_path: Path) -> None:
    source = _write(tmp_path, "template.hpp", CPP_TEMPLATE_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "Pick",
            "--source",
            str(source),
        ],
    )

    assert result.exit_code == 0
    assert "1: template <typename T>" in result.stdout
    assert "4:     return value;" in result.stdout


def test_quality_diagnostics_use_stderr_only_for_preprocess_warnings(tmp_path: Path) -> None:
    source = _write(tmp_path, "pragma.c", PREPROCESS_UNSUPPORTED_DIRECTIVE_SOURCE)
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "KeepPragma",
            "--source",
            str(source),
        ],
    )

    assert result.exit_code == 0
    assert "2: int KeepPragma(void)" in result.stdout
    assert "quality[preprocess]:" in result.stderr
    assert "repro:" in result.stderr


def test_quality_diagnostics_report_crlf_normalization(tmp_path: Path) -> None:
    source = _write_bytes(
        tmp_path,
        "crlf.c",
        b"int CrLf(void)\r\n{\r\n    return 1;\r\n}\r\n",
    )
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "CrLf",
            "--source",
            str(source),
        ],
    )

    assert result.exit_code == 0
    assert "1: int CrLf(void)" in result.stdout
    assert "quality[input]:" in result.stderr
    assert "CRLF" in result.stderr


def test_quality_diagnostics_report_bom_normalization(tmp_path: Path) -> None:
    source = _write_bytes(
        tmp_path,
        "bom.c",
        b"\xef\xbb\xbfint Bommed(void)\n{\n    return 1;\n}\n",
    )
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "Bommed",
            "--source",
            str(source),
        ],
    )

    assert result.exit_code == 0
    assert "1: int Bommed(void)" in result.stdout
    assert "quality[input]:" in result.stderr
    assert "BOM" in result.stderr


def test_non_utf8_input_fails(tmp_path: Path) -> None:
    source = _write_bytes(
        tmp_path,
        "non_utf8.c",
        "int Bad(void)\n{\n    // あ\n    return 1;\n}\n".encode("cp932"),
    )
    result = runner.invoke(
        app,
        [
            "function",
            "--name",
            "Bad",
            "--source",
            str(source),
        ],
    )

    assert result.exit_code == 1
    assert "UTF-8" in result.stderr


def test_missing_function_fails(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
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


def test_default_output_does_not_use_ansi_when_stdout_is_not_tty(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "--name", "FooFunction", "--source", str(source)])
    assert result.exit_code == 0
    assert ANSI_ESCAPE_PATTERN.search(result.stdout) is None


def test_color_option_forces_ansi_output(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "--name", "FooFunction", "--source", str(source), "--color"])
    assert result.exit_code == 0
    assert ANSI_ESCAPE_PATTERN.search(result.stdout) is not None
    assert "\x1b[2m" in result.stdout
    assert _strip_ansi(result.stdout).splitlines()[0] == " 4: int FooFunction(int command)"


def test_no_color_option_disables_ansi_output(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(
        app,
        ["function", "--name", "FooFunction", "--source", str(source), "--no-color"],
    )
    assert result.exit_code == 0
    assert ANSI_ESCAPE_PATTERN.search(result.stdout) is None


def test_should_use_color_prefers_explicit_value_over_tty() -> None:
    tty_stream = _FakeStream(is_tty=True)
    non_tty_stream = _FakeStream(is_tty=False)

    assert _should_use_color(True, non_tty_stream) is True
    assert _should_use_color(False, tty_stream) is False


def test_should_use_color_uses_tty_for_auto_mode() -> None:
    assert _should_use_color(None, _FakeStream(is_tty=True)) is True
    assert _should_use_color(None, _FakeStream(is_tty=False)) is False


def test_python_module_execution(tmp_path: Path) -> None:
    source = _write(tmp_path, "foo.c", SOURCE)
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
    result = subprocess.run(
        [sys.executable, "-m", "cifter", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == EXPECTED_VERSION


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _write_bytes(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", text)


class _FakeStream:
    def __init__(self, *, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty
