from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

import tree_sitter_c
import tree_sitter_cpp
from tree_sitter import Language, Node, Parser, Tree

from cifter.errors import CiftError
from cifter.model import (
    LanguageMode,
    LanguageResolution,
    ParseDiagnostic,
    ParseQualityReport,
    SourceSpan,
)
from cifter.preprocessor import preprocess_source

CPP_EXTENSIONS = {".cc", ".cpp", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++"}
QUALITY_COMPARE_EXTENSIONS = {".h"}


@dataclass(frozen=True)
class SourceFile:
    path: Path
    text: str
    text_bytes: bytes
    lines: tuple[str, ...]
    trailing_newline: bool
    line_start_bytes: tuple[int, ...]
    line_byte_lengths: tuple[int, ...]

    @classmethod
    def from_text(cls, path: Path, text: str) -> SourceFile:
        text_bytes = text.encode("utf-8")
        trailing_newline = text.endswith("\n")
        lines = tuple(text.splitlines())
        start_bytes: list[int] = []
        line_byte_lengths: list[int] = []
        offset = 0
        for index, line in enumerate(lines):
            line_bytes = line.encode("utf-8")
            start_bytes.append(offset)
            line_byte_lengths.append(len(line_bytes))
            offset += len(line_bytes)
            if index < len(lines) - 1 or trailing_newline:
                offset += 1
        return cls(
            path=path,
            text=text,
            text_bytes=text_bytes,
            lines=lines,
            trailing_newline=trailing_newline,
            line_start_bytes=tuple(start_bytes),
            line_byte_lengths=tuple(line_byte_lengths),
        )

    def span_for_lines(self, line_numbers: list[int]) -> SourceSpan:
        return SourceSpan(self.path, min(line_numbers), max(line_numbers))

    def line_text(self, line_no: int) -> str:
        return self.lines[line_no - 1]

    def line_start_byte(self, line_no: int) -> int:
        return self.line_start_bytes[line_no - 1]

    def slice_from_line_start(self, line_no: int, end_byte: int) -> str:
        start_byte = self.line_start_byte(line_no)
        return self.text_bytes[start_byte:end_byte].decode("utf-8").rstrip()

    def inline_spans_for_byte_range(self, start_byte: int, end_byte: int) -> tuple[tuple[int, int, int], ...]:
        if start_byte >= end_byte:
            return ()
        start_line_index = self._line_index_for_byte(start_byte)
        end_line_index = self._line_index_for_byte(end_byte - 1)
        spans: list[tuple[int, int, int]] = []
        for line_index in range(start_line_index, end_line_index + 1):
            line_no = line_index + 1
            line_start_byte = self.line_start_bytes[line_index]
            line_end_byte = line_start_byte + self.line_byte_lengths[line_index]
            span_start_byte = max(start_byte, line_start_byte)
            span_end_byte = min(end_byte, line_end_byte)
            if span_start_byte >= span_end_byte:
                continue
            segment_text = self.text_bytes[span_start_byte:span_end_byte].decode("utf-8")
            leading_trim = len(segment_text) - len(segment_text.lstrip())
            trailing_trim = len(segment_text) - len(segment_text.rstrip())
            trimmed_text = segment_text.strip()
            if not trimmed_text:
                continue
            start_column = len(self.text_bytes[line_start_byte:span_start_byte].decode("utf-8")) + leading_trim
            end_column = len(self.text_bytes[line_start_byte:span_end_byte].decode("utf-8")) - trailing_trim
            spans.append((line_no, start_column, end_column))
        return tuple(spans)

    def _line_index_for_byte(self, byte_offset: int) -> int:
        return bisect_right(self.line_start_bytes, byte_offset) - 1


@dataclass(frozen=True)
class ParsedSource:
    source: SourceFile
    tree: Tree
    language_name: str
    resolved_language: str
    language_resolution: LanguageResolution
    quality: ParseQualityReport


@dataclass(frozen=True)
class _NormalizedInput:
    text: str
    diagnostics: tuple[ParseDiagnostic, ...]


@dataclass(frozen=True)
class _ParseMetrics:
    has_error: bool
    error_count: int
    missing_count: int

    def sort_key(self) -> tuple[int, int, int]:
        return (int(self.has_error), self.error_count, self.missing_count)


@dataclass(frozen=True)
class _ParseAttempt:
    language_name: str
    tree: Tree
    metrics: _ParseMetrics


def parse_source(path: Path, defines: list[str], language: LanguageMode = "auto") -> ParsedSource:
    normalized_input = _read_and_normalize_source(path)
    preprocessed = preprocess_source(normalized_input.text, defines)
    source = SourceFile.from_text(path, preprocessed.text)
    attempt, resolution = _resolve_parse_attempt(path, source, language)
    diagnostics = normalized_input.diagnostics + preprocessed.diagnostics + _parse_diagnostics(attempt.metrics)
    quality = ParseQualityReport.from_diagnostics(diagnostics)
    return ParsedSource(
        source=source,
        tree=attempt.tree,
        language_name=attempt.language_name,
        resolved_language=attempt.language_name,
        language_resolution=resolution,
        quality=quality,
    )


def find_function(parsed: ParsedSource, name: str) -> Node:
    matches = [node for node in _iter_nodes(parsed.tree.root_node) if _is_function_named(node, parsed.source, name)]
    if not matches:
        raise CiftError(f"関数が見つかりません: {name}")
    if len(matches) > 1:
        raise CiftError(f"同名関数が複数見つかりました: {name}")
    return matches[0]


def function_body(function_node: Node) -> Node:
    definition = _function_definition_node(function_node)
    if definition is None:
        raise CiftError("関数本体を特定できません")
    for child in definition.named_children:
        if child.type == "compound_statement":
            return child
    raise CiftError("関数本体を特定できません")


def node_text(source: SourceFile, node: Node) -> str:
    return source.text_bytes[node.start_byte:node.end_byte].decode("utf-8")


def condition_text(source: SourceFile, node: Node) -> str:
    return node_text(source, node)


def _read_and_normalize_source(path: Path) -> _NormalizedInput:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CiftError("入力ファイルは UTF-8 または UTF-8 BOM 付き UTF-8 である必要があります") from error

    diagnostics: list[ParseDiagnostic] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        diagnostics.append(
            ParseDiagnostic(
                category="input",
                code="utf8_bom_normalized",
                message="UTF-8 BOM を除去して解析しました",
            )
        )

    has_crlf = "\r\n" in text
    if "\r" in text.replace("\r\n", ""):
        raise CiftError("改行コードは LF または CRLF のみ対応しています")

    if has_crlf:
        if "\n" in text.replace("\r\n", ""):
            diagnostics.append(
                ParseDiagnostic(
                    category="input",
                    code="mixed_newlines_normalized",
                    message="混在した改行コードを LF へ正規化して解析しました",
                )
            )
        else:
            diagnostics.append(
                ParseDiagnostic(
                    category="input",
                    code="crlf_normalized",
                    message="CRLF を LF へ正規化して解析しました",
                )
            )
        text = text.replace("\r\n", "\n")

    return _NormalizedInput(text=text, diagnostics=tuple(diagnostics))


def _resolve_parse_attempt(
    path: Path,
    source: SourceFile,
    language: LanguageMode,
) -> tuple[_ParseAttempt, LanguageResolution]:
    if language != "auto":
        return _parse_attempt(source.text_bytes, language), "explicit"

    suffix = path.suffix.lower()
    if suffix == ".c":
        return _parse_attempt(source.text_bytes, "c"), "extension"
    if suffix in CPP_EXTENSIONS:
        return _parse_attempt(source.text_bytes, "cpp"), "extension"
    if suffix in QUALITY_COMPARE_EXTENSIONS or suffix not in {".c", *CPP_EXTENSIONS}:
        return _best_parse_attempt(source.text_bytes, prefer_c=suffix == ".h"), "quality"
    return _parse_attempt(source.text_bytes, "c"), "extension"


def _best_parse_attempt(text_bytes: bytes, *, prefer_c: bool) -> _ParseAttempt:
    c_attempt = _parse_attempt(text_bytes, "c")
    cpp_attempt = _parse_attempt(text_bytes, "cpp")
    if c_attempt.metrics.sort_key() < cpp_attempt.metrics.sort_key():
        return c_attempt
    if cpp_attempt.metrics.sort_key() < c_attempt.metrics.sort_key():
        return cpp_attempt
    if prefer_c:
        return c_attempt
    return cpp_attempt


def _parse_attempt(text_bytes: bytes, language_name: str) -> _ParseAttempt:
    parser = _build_parser(language_name)
    tree = parser.parse(text_bytes)
    return _ParseAttempt(language_name=language_name, tree=tree, metrics=_collect_parse_metrics(tree.root_node))


def _collect_parse_metrics(root: Node) -> _ParseMetrics:
    error_count = 0
    missing_count = 0
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "ERROR":
            error_count += 1
        if bool(getattr(node, "is_missing", False)):
            missing_count += 1
        stack.extend(reversed(node.children))
    return _ParseMetrics(has_error=root.has_error, error_count=error_count, missing_count=missing_count)


def _parse_diagnostics(metrics: _ParseMetrics) -> tuple[ParseDiagnostic, ...]:
    diagnostics: list[ParseDiagnostic] = []
    if metrics.error_count:
        diagnostics.append(
            ParseDiagnostic(
                category="parse",
                code="error_nodes_detected",
                message=f"tree-sitter の ERROR ノードを {metrics.error_count} 件検出しました",
                details=(("count", str(metrics.error_count)),),
            )
        )
    if metrics.missing_count:
        diagnostics.append(
            ParseDiagnostic(
                category="parse",
                code="missing_nodes_detected",
                message=f"tree-sitter の MISSING ノードを {metrics.missing_count} 件検出しました",
                details=(("count", str(metrics.missing_count)),),
            )
        )
    return tuple(diagnostics)


def _build_parser(language_name: str) -> Parser:
    if language_name == "cpp":
        return Parser(Language(tree_sitter_cpp.language()))
    return Parser(Language(tree_sitter_c.language()))


def _iter_nodes(root: Node) -> list[Node]:
    nodes: list[Node] = []
    stack = [root]
    while stack:
        node = stack.pop()
        nodes.append(node)
        stack.extend(reversed(node.named_children))
    return nodes


def _is_function_named(node: Node, source: SourceFile, name: str) -> bool:
    if node.type == "function_definition" and node.parent is not None and node.parent.type == "template_declaration":
        return False
    definition = _function_definition_node(node)
    if definition is None:
        return False
    declarator = next(
        (child for child in definition.named_children if child.type.endswith("declarator")),
        None,
    )
    if declarator is None:
        return False
    return _extract_declarator_name(source, declarator) == name


def _function_definition_node(node: Node) -> Node | None:
    if node.type == "function_definition":
        return node
    if node.type == "template_declaration":
        for child in node.named_children:
            if child.type == "function_definition":
                return child
    return None


def _extract_declarator_name(source: SourceFile, node: Node) -> str | None:
    if node.type in {"identifier", "field_identifier"}:
        return node_text(source, node)
    if node.type == "qualified_identifier":
        return node_text(source, node).split("::")[-1]
    for child in node.named_children:
        if child.type in {"parameter_list", "template_parameter_list"}:
            continue
        name = _extract_declarator_name(source, child)
        if name is not None:
            return name
    return None
