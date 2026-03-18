from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from cifter.errors import CiftError
from cifter.extract_flow import extract_flow
from cifter.extract_function import extract_function
from cifter.extract_path import extract_path
from cifter.model import ExtractionResult, LanguageMode, ParseDiagnostic, TrackPath
from cifter.parser import ParsedSource, parse_source
from cifter.render import _should_use_color, print_result
from cifter.version import format_version_output

app = typer.Typer(no_args_is_help=True, help="C/C++ の関数実装を抽出する CLI")


def main() -> None:
    _normalize_stdio_encoding()
    app()


def _normalize_stdio_encoding() -> None:
    _normalize_stream_encoding(sys.stdout)
    _normalize_stream_encoding(sys.stderr)


def _normalize_stream_encoding(stream: object) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if not callable(reconfigure):
        return

    encoding = getattr(stream, "encoding", None)
    if isinstance(encoding, str) and encoding.lower().replace("_", "-") == "utf-8":
        return

    reconfigure(encoding="utf-8")


def _version_callback(value: bool) -> None:
    if not value:
        return
    typer.echo(format_version_output())
    raise typer.Exit()


@app.callback()
def common_options(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="バージョンを表示して終了する",
        ),
    ] = False,
) -> None:
    _ = version


SourceOption = Annotated[
    Path,
    typer.Option(
        "--source",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="解析するソースファイル",
    ),
]

ColorOption = Annotated[
    bool | None,
    typer.Option(
        "--color/--no-color",
        help="抽出結果のシンタックスハイライトを制御する",
    ),
]

LanguageOption = Annotated[
    LanguageMode,
    typer.Option(
        "--language",
        help="解析言語を指定する。既定は auto",
        case_sensitive=False,
    ),
]


@app.command("function")
def function_command(
    name: Annotated[str, typer.Option("--name", help="抽出する関数名")],
    source: SourceOption,
    language: LanguageOption = "auto",
    color: ColorOption = None,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    def task() -> tuple[ExtractionResult, ParsedSource]:
        parsed = parse_source(source, defines or [], language)
        return extract_function(parsed, name), parsed

    _run(task, color=color, source=source, language=language, defines=defines or [])


@app.command("flow")
def flow_command(
    function_name: Annotated[str, typer.Option("--function", help="対象関数名")],
    source: SourceOption,
    language: LanguageOption = "auto",
    track: Annotated[list[str], typer.Option("--track", help="保持するアクセスパス")] | None = None,
    highlight: Annotated[bool, typer.Option("--highlight", help="`--track` 一致箇所を追加強調する")] = False,
    color: ColorOption = None,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    def task() -> tuple[ExtractionResult, ParsedSource]:
        parsed = parse_source(source, defines or [], language)
        tracks = tuple(TrackPath.parse(value) for value in (track or []))
        include_highlights = bool(highlight and tracks and _should_use_color(color, sys.stdout))
        return extract_flow(
            parsed,
            function_name,
            tracks,
            include_highlights=include_highlights,
        ), parsed

    _run(task, color=color, source=source, language=language, defines=defines or [])


@app.command("path")
def path_command(
    function_name: Annotated[str, typer.Option("--function", help="対象関数名")],
    source: SourceOption,
    route: Annotated[list[str], typer.Option("--route", help="抽出する経路 DSL (`case[...]` / `if[...]` / `else-if[...]` を `/` で連結)")],
    language: LanguageOption = "auto",
    color: ColorOption = None,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    def task() -> tuple[ExtractionResult, ParsedSource]:
        parsed = parse_source(source, defines or [], language)
        return extract_path(parsed, function_name, route), parsed

    _run(task, color=color, source=source, language=language, defines=defines or [])


def _run(
    task: Callable[[], tuple[ExtractionResult, ParsedSource]],
    *,
    color: bool | None,
    source: Path,
    language: LanguageMode,
    defines: list[str],
) -> None:
    try:
        result, parsed = task()
        print_result(result, parsed.language_name, color=color)
        _print_quality_diagnostics(parsed, source=source, language=language, defines=defines)
    except CiftError as error:
        typer.echo(error.message, err=True)
        raise typer.Exit(code=1) from error


def _print_quality_diagnostics(
    parsed: ParsedSource,
    *,
    source: Path,
    language: LanguageMode,
    defines: list[str],
) -> None:
    if parsed.quality.level != "degraded":
        return

    categories = ("language", "parse", "preprocess", "input")
    for category in categories:
        messages = _aggregate_quality_messages(parsed.quality.diagnostics, category)
        if not messages:
            continue
        typer.echo(f"quality[{category}]: {'; '.join(messages)}", err=True)

    defines_text = ", ".join(defines) if defines else "-"
    typer.echo(
        "repro: "
        f"source={source} resolved_language={parsed.resolved_language} "
        f"--language={language} -D={defines_text}",
        err=True,
    )


def _aggregate_quality_messages(
    diagnostics: tuple[ParseDiagnostic, ...],
    category: str,
) -> list[str]:
    grouped: dict[str, list[ParseDiagnostic]] = {}
    for diagnostic in diagnostics:
        if diagnostic.category != category:
            continue
        grouped.setdefault(diagnostic.code, []).append(diagnostic)

    messages: list[str] = []
    for _code, items in grouped.items():
        message = items[0].message
        if len(items) > 1:
            message = f"{message} (x{len(items)})"
        messages.append(message)
    return messages
