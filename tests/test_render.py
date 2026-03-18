from __future__ import annotations

from io import StringIO
from pathlib import Path

from cifter.cli import app
from cifter.model import ExtractedLine, ExtractionResult, InlineHighlightSpan, SourceSpan
from cifter.render import _rendered_column_for_source_column, _should_use_color, print_result
from tests.support import (
    ANSI_ESCAPE_PATTERN,
    SOURCE,
    TRACK_SOURCE,
    FakeStream,
    runner,
    strip_ansi,
    write_text_file,
)


def test_flow_color_output_does_not_highlight_without_highlight_flag(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
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
    assert strip_ansi(color_result.stdout) == plain_result.stdout


def test_flow_color_output_highlights_track_matches_with_highlight_flag(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
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
    assert strip_ansi(color_result.stdout) == plain_result.stdout


def test_flow_highlight_is_noop_without_color_output(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "track.c", TRACK_SOURCE)
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
    assert strip_ansi(rendered).strip() == "12:         st->spl.status = status;"


def test_default_output_does_not_use_ansi_when_stdout_is_not_tty(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "--name", "FooFunction", "--source", str(source)])
    assert result.exit_code == 0
    assert ANSI_ESCAPE_PATTERN.search(result.stdout) is None


def test_color_option_forces_ansi_output(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "--name", "FooFunction", "--source", str(source), "--color"])
    assert result.exit_code == 0
    assert ANSI_ESCAPE_PATTERN.search(result.stdout) is not None
    assert "\x1b[2m" in result.stdout
    assert strip_ansi(result.stdout).splitlines()[0] == " 4: int FooFunction(int command)"


def test_no_color_option_disables_ansi_output(tmp_path: Path) -> None:
    source = write_text_file(tmp_path, "foo.c", SOURCE)
    result = runner.invoke(app, ["function", "--name", "FooFunction", "--source", str(source), "--no-color"])
    assert result.exit_code == 0
    assert ANSI_ESCAPE_PATTERN.search(result.stdout) is None


def test_should_use_color_prefers_explicit_value_over_tty() -> None:
    tty_stream = FakeStream(is_tty=True)
    non_tty_stream = FakeStream(is_tty=False)

    assert _should_use_color(True, non_tty_stream) is True
    assert _should_use_color(False, tty_stream) is False


def test_should_use_color_uses_tty_for_auto_mode() -> None:
    assert _should_use_color(None, FakeStream(is_tty=True)) is True
    assert _should_use_color(None, FakeStream(is_tty=False)) is False
