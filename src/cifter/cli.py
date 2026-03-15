from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from cifter.errors import CiftError
from cifter.extract_flow import extract_flow
from cifter.extract_function import extract_function
from cifter.extract_path import extract_path
from cifter.model import ExtractionResult, TrackPath
from cifter.parser import parse_source
from cifter.render import print_result
from cifter.version import format_version_output

app = typer.Typer(no_args_is_help=True, help="C/C++ の関数実装を抽出する CLI")


def main() -> None:
    app()


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


@app.command("function")
def function_command(
    name: Annotated[str, typer.Option("--name", help="抽出する関数名")],
    source: SourceOption,
    color: ColorOption = None,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    def task() -> tuple[ExtractionResult, str]:
        parsed = parse_source(source, defines or [])
        return extract_function(parsed, name), parsed.language_name

    _run(task, color=color)


@app.command("flow")
def flow_command(
    function_name: Annotated[str, typer.Option("--function", help="対象関数名")],
    source: SourceOption,
    track: Annotated[list[str], typer.Option("--track", help="保持するアクセスパス")] | None = None,
    color: ColorOption = None,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    def task() -> tuple[ExtractionResult, str]:
        parsed = parse_source(source, defines or [])
        tracks = tuple(TrackPath.parse(value) for value in (track or []))
        return extract_flow(parsed, function_name, tracks), parsed.language_name

    _run(task, color=color)


@app.command("path")
def path_command(
    function_name: Annotated[str, typer.Option("--function", help="対象関数名")],
    source: SourceOption,
    route: Annotated[str, typer.Option("--route", help="抽出する経路 DSL")],
    color: ColorOption = None,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    def task() -> tuple[ExtractionResult, str]:
        parsed = parse_source(source, defines or [])
        return extract_path(parsed, function_name, route), parsed.language_name

    _run(task, color=color)


def _run(task: Callable[[], tuple[ExtractionResult, str]], *, color: bool | None) -> None:
    try:
        result, language_name = task()
        print_result(result, language_name, color=color)
    except CiftError as error:
        typer.echo(error.message, err=True)
        raise typer.Exit(code=1) from error
