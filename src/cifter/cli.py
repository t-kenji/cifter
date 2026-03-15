from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from cifter.errors import CiftError
from cifter.extract_flow import extract_flow
from cifter.extract_function import extract_function
from cifter.extract_path import extract_path
from cifter.model import TrackPath
from cifter.parser import parse_source
from cifter.render import render_result

app = typer.Typer(no_args_is_help=True, help="C/C++ の関数実装を抽出する CLI")


def main() -> None:
    app()


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


@app.command("function")
def function_command(
    name: Annotated[str, typer.Option("--name", help="抽出する関数名")],
    source: SourceOption,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    _run(lambda: render_result(extract_function(parse_source(source, defines or []), name)))


@app.command("flow")
def flow_command(
    function_name: Annotated[str, typer.Option("--function", help="対象関数名")],
    source: SourceOption,
    track: Annotated[list[str], typer.Option("--track", help="保持するアクセスパス")] | None = None,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    def task() -> str:
        parsed = parse_source(source, defines or [])
        tracks = tuple(TrackPath.parse(value) for value in (track or []))
        return render_result(extract_flow(parsed, function_name, tracks))

    _run(task)


@app.command("path")
def path_command(
    function_name: Annotated[str, typer.Option("--function", help="対象関数名")],
    source: SourceOption,
    route: Annotated[str, typer.Option("--route", help="抽出する経路 DSL")],
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
) -> None:
    def task() -> str:
        parsed = parse_source(source, defines or [])
        return render_result(extract_path(parsed, function_name, route))

    _run(task)


def _run(task: Callable[[], str]) -> None:
    try:
        typer.echo(task())
    except CiftError as error:
        typer.echo(error.message, err=True)
        raise typer.Exit(code=1) from error
