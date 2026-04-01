from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from cifter.errors import CiftError
from cifter.model import FormatMode, LanguageMode, RunResult
from cifter.render_json import render_result_json
from cifter.render_text import print_result_text
from cifter.run import resolve_input_files, resolve_output_format, run_flow, run_function, run_route
from cifter.version import format_version_output

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="C/C++ ソースを高速に切り出す CLI",
)


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


FilesFromOption = Annotated[
    list[str] | None,
    typer.Option("--files-from", help="1 行 1 path の一覧 file。`-` で標準入力から読む"),
]
ColorOption = Annotated[
    bool | None,
    typer.Option("--color/--no-color", help="text 出力のシンタックスハイライトを制御する"),
]
LanguageOption = Annotated[
    LanguageMode,
    typer.Option("--language", help="解析言語を指定する。既定は auto", case_sensitive=False),
]
FormatOption = Annotated[
    FormatMode,
    typer.Option(
        "--format",
        help="出力形式を指定する。auto は TTY=text、非 TTY=json。--color/--no-color を明示した auto は text",
        case_sensitive=False,
    ),
]
StrictInputsOption = Annotated[
    bool,
    typer.Option("--strict-inputs", help="未一致 file を warning ではなく失敗として扱う"),
]


@app.command("function", help="関数実装全体を切り出す")
def function_command(
    symbol: Annotated[str, typer.Argument(help="抽出する関数名")],
    inputs: Annotated[list[Path] | None, typer.Argument(help="対象 file または dir。複数指定可")] = None,
    *,
    language: LanguageOption = "auto",
    format_mode: FormatOption = "auto",
    color: ColorOption = None,
    strict_inputs: StrictInputsOption = False,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
    files_from: FilesFromOption = None,
) -> None:
    _exit_with_run_result(
        lambda resolved_inputs: run_function(
            symbol,
            inputs=resolved_inputs,
            defines=_string_values(defines),
            language=language,
            strict_inputs=strict_inputs,
        ),
        inputs=_path_values(inputs),
        files_from=_string_values(files_from),
        format_mode=format_mode,
        color=color,
    )


@app.command("flow", help="制御構造の骨格と追跡行を切り出す")
def flow_command(
    symbol: Annotated[str, typer.Argument(help="抽出する関数名")],
    inputs: Annotated[list[Path] | None, typer.Argument(help="対象 file または dir。複数指定可")] = None,
    *,
    language: LanguageOption = "auto",
    track: Annotated[list[str] | None, typer.Option("--track", help="保持するアクセスパス")] = None,
    highlight: Annotated[
        bool, typer.Option("--highlight", help="`--track` 一致箇所を追加強調する")
    ] = False,
    format_mode: FormatOption = "auto",
    color: ColorOption = None,
    strict_inputs: StrictInputsOption = False,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
    files_from: FilesFromOption = None,
) -> None:
    _exit_with_run_result(
        lambda resolved_inputs: run_flow(
            symbol,
            inputs=resolved_inputs,
            defines=_string_values(defines),
            language=language,
            track=_string_values(track),
            include_highlights=highlight,
            strict_inputs=strict_inputs,
        ),
        inputs=_path_values(inputs),
        files_from=_string_values(files_from),
        format_mode=format_mode,
        color=color,
    )


@app.command("route", help="指定 route DSL に沿う枝だけを切り出す")
def route_command(
    symbol: Annotated[str, typer.Argument(help="抽出する関数名")],
    inputs: Annotated[list[Path] | None, typer.Argument(help="対象 file または dir。複数指定可")] = None,
    *,
    route: Annotated[
        list[str] | None,
        typer.Option("--route", help="抽出する route DSL。複数指定可"),
    ] = None,
    infer_from_line: Annotated[
        int | None,
        typer.Option("--infer-from-line", help="指定行を含む最も深い branch route を推論する"),
    ] = None,
    language: LanguageOption = "auto",
    format_mode: FormatOption = "auto",
    color: ColorOption = None,
    strict_inputs: StrictInputsOption = False,
    defines: Annotated[
        list[str] | None,
        typer.Option("--define", "-D", help="条件分岐評価に使うマクロ定義"),
    ] = None,
    files_from: FilesFromOption = None,
) -> None:
    _exit_with_run_result(
        lambda resolved_inputs: run_route(
            symbol,
            inputs=resolved_inputs,
            defines=_string_values(defines),
            language=language,
            routes=_string_values(route),
            infer_from_line=infer_from_line,
            strict_inputs=strict_inputs,
        ),
        inputs=_path_values(inputs),
        files_from=_string_values(files_from),
        format_mode=format_mode,
        color=color,
    )


def _string_values(values: list[str] | None) -> list[str]:
    return values or []


def _path_values(values: list[Path] | None) -> list[Path]:
    return values or []


def _exit_with_run_result(
    task: Callable[[tuple[Path, ...]], RunResult],
    *,
    inputs: list[Path],
    files_from: list[str],
    format_mode: FormatMode,
    color: bool | None,
) -> None:
    run_result = _run_with_input_resolution(
        task,
        inputs=inputs,
        files_from=files_from,
        format_mode=format_mode,
        color=color,
    )
    raise typer.Exit(code=0 if _succeeded(run_result) else 1)


def _run_with_input_resolution(
    task: Callable[[tuple[Path, ...]], RunResult],
    *,
    inputs: list[Path],
    files_from: list[str],
    format_mode: FormatMode,
    color: bool | None,
) -> RunResult:
    try:
        resolved_inputs = resolve_input_files(inputs, files_from=files_from)
        run_result = task(resolved_inputs)
        _write_run_result(run_result, format_mode=format_mode, color=color)
        return run_result
    except CiftError as error:
        typer.echo(error.message, err=True)
        raise typer.Exit(code=1) from error


def _write_run_result(run_result: RunResult, *, format_mode: FormatMode, color: bool | None) -> None:
    output_format = _resolved_output_format(format_mode, color)
    if output_format == "json":
        typer.echo(render_result_json(run_result))
        return

    print_result_text(run_result, color=color)
    for diagnostic in run_result.diagnostics:
        prefix = f"{diagnostic.file}: " if diagnostic.file is not None else ""
        typer.echo(f"{prefix}{diagnostic.message}", err=True)


def _resolved_output_format(format_mode: FormatMode, color: bool | None) -> FormatMode:
    if format_mode == "auto" and color is not None:
        return "text"
    return resolve_output_format(format_mode, is_tty=getattr(sys.stdout, "isatty", lambda: False)())


def _succeeded(run_result: RunResult) -> bool:
    return not any(diagnostic.severity == "error" for diagnostic in run_result.diagnostics)
