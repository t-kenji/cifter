from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from tree_sitter import Node

from cifter.errors import CiftError
from cifter.extract_flow import extract_flow_node
from cifter.extract_function import extract_function_node
from cifter.extract_route import extract_route_node, infer_route_for_line
from cifter.model import (
    SUPPORTED_SOURCE_EXTENSIONS,
    CommandName,
    ExtractionItem,
    ExtractionResult,
    FormatMode,
    LanguageMode,
    RouteSegment,
    RunDiagnostic,
    RunResult,
    TrackPath,
    parse_route,
)
from cifter.parser import ParsedSource, find_functions, parse_source
from cifter.version import get_version

type _Extractor = Callable[[ParsedSource, Node], ExtractionResult]


def resolve_output_format(format_mode: FormatMode, *, is_tty: bool) -> FormatMode:
    if format_mode == "auto":
        return "text" if is_tty else "json"
    return format_mode


def resolve_input_files(
    inputs: Sequence[Path],
    *,
    files_from: Sequence[str],
    stdin: object | None = None,
) -> tuple[Path, ...]:
    stdin_stream = stdin or sys.stdin
    specs = list(inputs)
    for item in files_from:
        specs.extend(_read_input_specs(item, stdin_stream))
    if not specs:
        raise CiftError("対象入力がありません。file/dir または --files-from を指定してください")

    resolved: dict[str, Path] = {}
    for spec in specs:
        for path in _expand_input_path(spec):
            resolved[str(path)] = path
    if not resolved:
        raise CiftError("対象入力がありません。C/C++ ソースが見つかりませんでした")
    return tuple(path for _, path in sorted(resolved.items()))


def run_function(
    symbol: str,
    *,
    inputs: Sequence[Path],
    defines: list[str],
    language: LanguageMode,
    strict_inputs: bool = False,
) -> RunResult:
    return _run_command(
        "function",
        symbol,
        inputs=inputs,
        defines=defines,
        language=language,
        strict_inputs=strict_inputs,
    )


def run_flow(
    symbol: str,
    *,
    inputs: Sequence[Path],
    defines: list[str],
    language: LanguageMode,
    track: Sequence[str],
    include_highlights: bool,
    strict_inputs: bool = False,
) -> RunResult:
    tracks = tuple(TrackPath.parse(value) for value in track)
    return _run_command(
        "flow",
        symbol,
        inputs=inputs,
        defines=defines,
        language=language,
        tracks=tracks,
        include_highlights=include_highlights,
        strict_inputs=strict_inputs,
    )


def run_route(
    symbol: str,
    *,
    inputs: Sequence[Path],
    defines: list[str],
    language: LanguageMode,
    routes: Sequence[str],
    infer_from_line: int | None = None,
    strict_inputs: bool = False,
) -> RunResult:
    if infer_from_line is not None:
        if routes:
            raise CiftError("--route と --infer-from-line は併用できません")
        return _run_route_infer_from_line(
            symbol,
            inputs=inputs,
            defines=defines,
            language=language,
            infer_from_line=infer_from_line,
        )

    route_values = tuple(routes)
    if not route_values:
        raise CiftError("--route または --infer-from-line を指定してください")
    parsed_routes = tuple(parse_route(route) for route in route_values)
    return _run_command(
        "route",
        symbol,
        inputs=inputs,
        defines=defines,
        language=language,
        routes=route_values,
        parsed_routes=parsed_routes,
        strict_inputs=strict_inputs,
    )


def _run_route_infer_from_line(
    symbol: str,
    *,
    inputs: Sequence[Path],
    defines: list[str],
    language: LanguageMode,
    infer_from_line: int,
) -> RunResult:
    if infer_from_line <= 0:
        raise CiftError("--infer-from-line は 1 以上の行番号で指定してください")
    if len(inputs) != 1:
        raise CiftError("--infer-from-line は単一 input file のときだけ指定できます")

    input_file = inputs[0]
    parsed = parse_source(input_file, defines, language)
    matches = find_functions(parsed, symbol)
    if not matches:
        raise CiftError(f"関数が見つかりません: {symbol}")

    containing = tuple(function for function in matches if _node_contains_line(function, infer_from_line))
    if not containing:
        raise CiftError(f"行 {infer_from_line} を含む関数が見つかりません: {symbol}")
    if len(containing) > 1:
        raise CiftError(f"行 {infer_from_line} を含む同名関数が複数見つかりました: {symbol}")

    inferred_route = infer_route_for_line(parsed, containing[0], infer_from_line)
    parsed_routes = (parse_route(inferred_route),)
    extraction = extract_route_node(parsed, containing[0], parsed_routes)
    result = _build_extraction_item(
        "route",
        input_file,
        symbol,
        parsed,
        extraction,
        (inferred_route,),
    )
    return RunResult(
        tool_version=get_version(),
        command="route",
        inputs=(input_file,),
        results=(result,),
        diagnostics=(),
    )


def _run_command(
    command: CommandName,
    symbol: str,
    *,
    inputs: Sequence[Path],
    defines: list[str],
    language: LanguageMode,
    tracks: tuple[TrackPath, ...] = (),
    routes: tuple[str, ...] = (),
    parsed_routes: tuple[tuple[RouteSegment, ...], ...] = (),
    include_highlights: bool = False,
    strict_inputs: bool = False,
) -> RunResult:
    cache: dict[tuple[Path, tuple[str, ...], str], ParsedSource] = {}
    results: list[ExtractionItem] = []
    diagnostics: list[RunDiagnostic] = []
    define_values = tuple(defines)
    extract = _extractor_for_command(
        command,
        tracks=tracks,
        parsed_routes=parsed_routes,
        include_highlights=include_highlights,
    )

    for input_file in inputs:
        try:
            parsed = _get_parsed_source(cache, input_file, define_values, language)
            matches = find_functions(parsed, symbol)
            if not matches:
                diagnostics.append(_function_not_found_diagnostic(symbol, input_file, strict_inputs))
                continue

            for function_node in matches:
                results.append(
                    _build_extraction_item(
                        command,
                        input_file,
                        symbol,
                        parsed,
                        extract(parsed, function_node),
                        routes,
                    )
                )
        except CiftError as error:
            diagnostics.append(
                RunDiagnostic(
                    severity="error",
                    code=f"{command}_failed",
                    message=error.message,
                    file=input_file,
                )
            )

    if not results and not any(diagnostic.severity == "error" for diagnostic in diagnostics):
        diagnostics.append(
            RunDiagnostic(severity="error", code="no_results", message="一致する結果がありません")
        )

    return RunResult(
        tool_version=get_version(),
        command=command,
        inputs=tuple(inputs),
        results=tuple(results),
        diagnostics=tuple(diagnostics),
    )


def _extractor_for_command(
    command: CommandName,
    *,
    tracks: tuple[TrackPath, ...],
    parsed_routes: tuple[tuple[RouteSegment, ...], ...],
    include_highlights: bool,
) -> _Extractor:
    if command == "function":
        return extract_function_node
    if command == "flow":
        return lambda parsed, function_node: extract_flow_node(
            parsed,
            function_node,
            tracks,
            include_highlights=include_highlights,
        )
    return lambda parsed, function_node: extract_route_node(parsed, function_node, parsed_routes)


def _function_not_found_diagnostic(symbol: str, path: Path, strict_inputs: bool) -> RunDiagnostic:
    return RunDiagnostic(
        severity="error" if strict_inputs else "warning",
        code="function_not_found",
        message=f"関数が見つかりません: {symbol}",
        file=path,
    )


def _build_extraction_item(
    command: CommandName,
    input_file: Path,
    symbol: str,
    parsed: ParsedSource,
    extraction: ExtractionResult,
    routes: tuple[str, ...],
) -> ExtractionItem:
    return ExtractionItem(
        file=input_file,
        symbol=symbol,
        kind=command,
        span=extraction.span,
        language=parsed.language_name,
        lines=extraction.lines,
        diagnostics=parsed.diagnostics,
        routes=routes,
    )


def _get_parsed_source(
    cache: dict[tuple[Path, tuple[str, ...], str], ParsedSource],
    path: Path,
    defines: tuple[str, ...],
    language: LanguageMode,
) -> ParsedSource:
    key = (path, defines, language)
    cached = cache.get(key)
    if cached is not None:
        return cached
    parsed = parse_source(path, list(defines), language)
    cache[key] = parsed
    return parsed


def _node_contains_line(node: Node, line_no: int) -> bool:
    start_line = node.start_point.row + 1
    end_line = node.end_point.row + 1
    return start_line <= line_no <= end_line


def _read_input_specs(path_value: str, stdin_stream: object) -> tuple[Path, ...]:
    if path_value == "-":
        text = getattr(stdin_stream, "read", None)
        if not callable(text):
            raise CiftError("標準入力から path 一覧を読めません")
        raw = text()
        if not isinstance(raw, str):
            raise CiftError("標準入力から UTF-8 text として path 一覧を読めません")
        return _paths_from_text(raw)

    source_path = Path(path_value).expanduser()
    try:
        raw = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise CiftError(f"--files-from は UTF-8 text である必要があります: {path_value}") from error
    except OSError as error:
        raise CiftError(f"--files-from を読めません: {path_value}") from error
    return _paths_from_text(raw)


def _paths_from_text(raw: str) -> tuple[Path, ...]:
    return tuple(Path(line.strip()) for line in raw.splitlines() if line.strip())


def _expand_input_path(path: Path) -> Iterable[Path]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise CiftError(f"対象が見つかりません: {path}")
    if resolved.is_file():
        if resolved.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS:
            yield resolved
        return
    if not resolved.is_dir():
        return
    yield from _iter_directory_sources(resolved)


def _iter_directory_sources(root: Path) -> Iterable[Path]:
    for current_root, dir_names, file_names in os.walk(root):
        dir_names.sort()
        file_names.sort()
        current_path = Path(current_root)
        for name in file_names:
            child = current_path / name
            if child.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS:
                yield child.resolve()
