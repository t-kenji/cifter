from __future__ import annotations

from pathlib import Path

from cifter.cli import app
from tests.support import (
    AMBIGUOUS_FOR_SOURCE,
    AMBIGUOUS_SOURCE,
    BLOCK_CASE_SOURCE,
    CPP_PATH_SOURCE,
    DEFAULT_SOURCE,
    DO_WHILE_ROUTE_SOURCE,
    ELSE_SOURCE,
    LOOP_PATH_SOURCE,
    PATH_TRAILING_SOURCE,
    QUALIFIED_CASE_SOURCE,
    SOURCE,
    WHILE_ROUTE_SOURCE,
    demo_source,
    runner,
    write_text_file,
)


def test_path_keeps_selected_case_if_branch_and_following_statements(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "route_tail.c", PATH_TRAILING_SOURCE)
    result = runner.invoke(
        app,
        ["path", "--function", "RouteTail", "--source", str(source), "--route", "case 1 > if x > 0"],
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
    source = write_text_file(tmp_path, "foo.c", SOURCE)
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
    source = write_text_file(tmp_path, "else_route.c", ELSE_SOURCE)
    result = runner.invoke(app, ["path", "--function", "ElseRoute", "--source", str(source), "--route", "else"])
    assert result.exit_code == 0
    assert "3:     if (x > 0) {" in result.stdout
    assert "5:     } else {" in result.stdout
    assert "6:         WorkB();" in result.stdout
    assert "9:     After();" in result.stdout
    assert "10:     return 3;" in result.stdout
    assert "WorkA();" not in result.stdout


def test_path_renders_ellipsis_for_omitted_regions(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "else_route.c", ELSE_SOURCE)
    result = runner.invoke(app, ["path", "--function", "ElseRoute", "--source", str(source), "--route", "else"])
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
    source = write_text_file(tmp_path, "default_route.c", DEFAULT_SOURCE)
    result = runner.invoke(app, ["path", "--function", "DefaultRoute", "--source", str(source), "--route", "default"])
    assert result.exit_code == 0
    assert "6:     default:" in result.stdout
    assert "7:         HandleDefault();" in result.stdout
    assert "8:         break;" in result.stdout
    assert "case 1" not in result.stdout


def test_path_supports_nested_route_inside_case_block(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "block_case.c", BLOCK_CASE_SOURCE)
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
    source = write_text_file(tmp_path, "block_case.c", BLOCK_CASE_SOURCE)
    result = runner.invoke(app, ["path", "--function", "BlockCaseRoute", "--source", str(source), "--route", "default"])
    assert result.exit_code == 0
    assert "13:     default:" in result.stdout
    assert "14:     {" in result.stdout
    assert "15:         break;" in result.stdout
    assert "16:     }" in result.stdout
    assert "case REQ_A" not in result.stdout


def test_path_supports_loop_segment_before_case_route(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "loop_route.c", LOOP_PATH_SOURCE)
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
    source = write_text_file(tmp_path, "while_route.c", WHILE_ROUTE_SOURCE)
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
    source = write_text_file(tmp_path, "do_while_route.c", DO_WHILE_ROUTE_SOURCE)
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


def test_path_stops_trailing_statements_before_next_branching_sibling() -> None:
    source = demo_source()
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "FooFunction",
            "--source",
            str(source),
            "--route",
            "case CMD_LOOP > for",
        ],
    )
    assert result.exit_code == 0
    assert "90:     case CMD_LOOP:" in result.stdout
    assert "91:         for (i = 0; i < 4; i++) {" in result.stdout
    assert "99:         }" in result.stdout
    assert "101:        while (ctx->retry_count < 2) {" not in result.stdout
    assert "109:        do {" not in result.stdout
    assert "112:        break;" not in result.stdout


def test_path_supports_multiple_routes_with_shared_ancestor() -> None:
    source = demo_source()
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "FooFunction",
            "--source",
            str(source),
            "--route",
            "case CMD_LOOP > while (ctx->retry_count < 2) > if (ctx->retry_count == 1)",
            "--route",
            "case CMD_LOOP > for",
        ],
    )
    assert result.exit_code == 0
    assert result.stdout.count("90:     case CMD_LOOP:") == 1
    assert "91:         for (i = 0; i < 4; i++) {" in result.stdout
    assert "101:         while (ctx->retry_count < 2) {" in result.stdout
    assert "103:" in result.stdout
    assert "if (ctx->retry_count == 1) {" in result.stdout
    assert "106:" in result.stdout
    assert "break;" in result.stdout
    assert "109:        do {" not in result.stdout
    assert "112:        break;" not in result.stdout
    assert result.stdout.index("91:         for (i = 0; i < 4; i++) {") < result.stdout.index(
        "101:         while (ctx->retry_count < 2) {"
    )


def test_path_multiple_routes_merge_if_chain_siblings(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
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
            "--route",
            "case CMD_HOGE > if ret == OK",
        ],
    )
    assert result.exit_code == 0
    assert result.stdout.count("13:         if (ret == OK) {") == 1
    assert "14:             state = DONE;" in result.stdout
    assert "15:             return state;" in result.stdout
    assert "16:         } else if (errno == EINT) {" in result.stdout
    assert "17:             state = RETRY;" in result.stdout
    assert "18:             return -2;" in result.stdout
    assert "} else {" not in result.stdout


def test_path_duplicate_routes_do_not_duplicate_output(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "else_route.c", ELSE_SOURCE)
    single = runner.invoke(app, ["path", "--function", "ElseRoute", "--source", str(source), "--route", "else"])
    duplicate = runner.invoke(
        app,
        [
            "path",
            "--function",
            "ElseRoute",
            "--source",
            str(source),
            "--route",
            "else",
            "--route",
            "else",
        ],
    )
    assert single.exit_code == 0
    assert duplicate.exit_code == 0
    assert duplicate.stdout == single.stdout


def test_multiple_path_routes_fail_if_any_route_is_invalid(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "FooFunction",
            "--source",
            str(source),
            "--route",
            "case CMD_HOGE > if ret == OK",
            "--route",
            "case CMD_HOGE > if ret == NG",
        ],
    )
    assert result.exit_code == 1
    assert "--route 'case CMD_HOGE > if ret == NG'" in result.stderr
    assert "見つかりません" in result.stderr


def test_invalid_route_fails(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(
        app,
        ["path", "--function", "FooFunction", "--source", str(source), "--route", "case CMD_HOGE > else > if errno == EINT"],
    )
    assert result.exit_code == 1
    assert "else if" in result.stderr


def test_path_does_not_skip_loop_implicitly(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "loop_route.c", LOOP_PATH_SOURCE)
    result = runner.invoke(
        app,
        ["path", "--function", "LoopRoute", "--source", str(source), "--route", "else > case STS_IDLE"],
    )
    assert result.exit_code == 1
    assert "見つかりません" in result.stderr


def test_ambiguous_route_fails(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "ambiguous.c", AMBIGUOUS_SOURCE)
    result = runner.invoke(app, ["path", "--function", "Ambiguous", "--source", str(source), "--route", "if x > 0"])
    assert result.exit_code == 1
    assert "複数" in result.stderr


def test_ambiguous_for_route_fails(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "ambiguous_for.c", AMBIGUOUS_FOR_SOURCE)
    result = runner.invoke(app, ["path", "--function", "AmbiguousFor", "--source", str(source), "--route", "for"])
    assert result.exit_code == 1
    assert "複数" in result.stderr


def test_cpp_path_keeps_selected_branch(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "route.cpp", CPP_PATH_SOURCE)
    result = runner.invoke(app, ["path", "--function", "Route", "--source", str(source), "--route", "if value > 0"])
    assert result.exit_code == 0
    assert "4:     if (value > 0) {" in result.stdout
    assert "5:         return 1;" in result.stdout
    assert "else" not in result.stdout


def test_path_supports_qualified_case_labels(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "qualified.cpp", QUALIFIED_CASE_SOURCE)
    result = runner.invoke(
        app,
        [
            "path",
            "--function",
            "QualifiedRoute",
            "--source",
            str(source),
            "--route",
            "case ns::State::Idle",
        ],
    )
    assert result.exit_code == 0
    assert "8:     case ns::State::Idle:" in result.stdout
    assert "9:         return 1;" in result.stdout
    assert "Busy" not in result.stdout
