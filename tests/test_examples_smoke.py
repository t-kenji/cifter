from __future__ import annotations

import json

from cifter.cli import app
from tests.support import example_path, runner


def test_quickstart_examples_cover_function_flow_and_route() -> None:
    source = example_path("quickstart", "decide_mode.c")

    function_result = runner.invoke(app, ["function", "DecideMode", str(source), "--format", "text"])
    flow_result = runner.invoke(app, ["flow", "DecideMode", str(source), "--track", "state", "--format", "text"])
    route_result = runner.invoke(
        app,
        ["route", "DecideMode", str(source), "--route", "else-if[value == 10]", "--format", "text"],
    )

    assert function_result.exit_code == 0
    assert "1: int DecideMode(int value)" in function_result.stdout
    assert "7:     } else if (value == 10) {" in function_result.stdout

    assert flow_result.exit_code == 0
    assert "3:     int state = 0;" in flow_result.stdout
    assert "8:         state = 2;" in flow_result.stdout

    assert route_result.exit_code == 0
    assert "7:     } else if (value == 10) {" in route_result.stdout
    assert "8:         state = 2;" in route_result.stdout


def test_showcase_c_flow_highlight_and_multiple_routes_work() -> None:
    source = example_path("showcase", "c", "control_flow.c")

    flow_result = runner.invoke(
        app,
        [
            "flow",
            "DispatchCommand",
            str(source),
            "--track",
            "ctx->state",
            "--track",
            "ret",
            "--highlight",
            "--format",
            "json",
        ],
    )
    route_result = runner.invoke(
        app,
        [
            "route",
            "DispatchCommand",
            str(source),
            "--route",
            "case[CMD_HOGE]/else-if[ret == RETRY_LATER]",
            "--route",
            "case[CMD_LOOP]/while/if[ctx->retry_count == 1]",
            "--format",
            "text",
        ],
    )

    assert flow_result.exit_code == 0
    flow_payload = json.loads(flow_result.stdout)
    flow_lines = flow_payload["results"][0]["rendered_lines"]
    assert any("ctx->state = 210;" in line["text"] for line in flow_lines)
    assert any(line["highlights"] for line in flow_lines)

    assert route_result.exit_code == 0
    assert "else if (ret == RETRY_LATER)" in route_result.stdout
    assert "if (ctx->retry_count == 1)" in route_result.stdout


def test_showcase_c_preprocessor_example_uses_defines() -> None:
    source = example_path("showcase", "c", "preprocess.c")

    result = runner.invoke(
        app,
        [
            "function",
            "ConfigureBuild",
            str(source),
            "-D",
            "ENABLE_FAST_PATH",
            "-D",
            "FEATURE_LEVEL=2",
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 0
    assert "ctx->state = LOCAL_PHASE_STATE;" in result.stdout
    assert "ctx->inner.value = ctx->inner.value + 10;" in result.stdout


def test_showcase_cpp_examples_cover_member_template_and_routes() -> None:
    member_source = example_path("showcase", "cpp", "member_workflow.cpp")
    route_source = example_path("showcase", "cpp", "route_cases.cpp")

    member_result = runner.invoke(app, ["function", "Process", str(member_source), "--format", "text"])
    template_result = runner.invoke(app, ["function", "PickNonZero", str(member_source), "--format", "text"])
    else_route_result = runner.invoke(
        app,
        ["route", "RouteMode", str(route_source), "--route", "else", "--format", "text"],
    )
    case_route_result = runner.invoke(
        app,
        [
            "route",
            "QualifiedDispatch",
            str(route_source),
            "--route",
            "case[ns::State::Busy]",
            "--format",
            "text",
        ],
    )

    assert member_result.exit_code == 0
    assert "int Worker::Process(WorkerContext *ctx, int value)" in member_result.stdout

    assert template_result.exit_code == 0
    assert "template <typename T>" in template_result.stdout
    assert "T PickNonZero(T current, T fallback)" in template_result.stdout

    assert else_route_result.exit_code == 0
    assert "} else {" in else_route_result.stdout

    assert case_route_result.exit_code == 0
    assert "case ns::State::Busy:" in case_route_result.stdout


def test_multi_input_examples_match_directory_and_files_from() -> None:
    source_dir = example_path("multi_input")
    targets = example_path("multi_input", "targets.txt")

    dir_result = runner.invoke(app, ["function", "MirrorValue", str(source_dir), "--format", "json"])
    files_result = runner.invoke(
        app,
        ["function", "MirrorValue", "--files-from", str(targets), "--format", "json"],
    )

    assert dir_result.exit_code == 0
    assert files_result.exit_code == 0
    assert json.loads(dir_result.stdout)["results"] == json.loads(files_result.stdout)["results"]
