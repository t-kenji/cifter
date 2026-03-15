from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import tree_sitter_c
import tree_sitter_cpp
from tree_sitter import Language, Node, Parser, Tree

from cifter.errors import CiftError
from cifter.model import SourceSpan
from cifter.preprocessor import preprocess_source

CPP_EXTENSIONS = {".cc", ".cpp", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++"}


@dataclass(frozen=True)
class SourceFile:
    path: Path
    text: str
    lines: tuple[str, ...]
    trailing_newline: bool
    line_start_bytes: tuple[int, ...]

    @classmethod
    def from_text(cls, path: Path, text: str) -> SourceFile:
        trailing_newline = text.endswith("\n")
        lines = tuple(text.splitlines())
        start_bytes: list[int] = []
        offset = 0
        for index, line in enumerate(lines):
            start_bytes.append(offset)
            offset += len(line.encode("utf-8"))
            if index < len(lines) - 1 or trailing_newline:
                offset += 1
        return cls(
            path=path,
            text=text,
            lines=lines,
            trailing_newline=trailing_newline,
            line_start_bytes=tuple(start_bytes),
        )

    def span_for_lines(self, line_numbers: list[int]) -> SourceSpan:
        return SourceSpan(self.path, min(line_numbers), max(line_numbers))

    def line_text(self, line_no: int) -> str:
        return self.lines[line_no - 1]

    def line_start_byte(self, line_no: int) -> int:
        return self.line_start_bytes[line_no - 1]

    def slice_from_line_start(self, line_no: int, end_byte: int) -> str:
        start_byte = self.line_start_byte(line_no)
        return self.text.encode("utf-8")[start_byte:end_byte].decode("utf-8").rstrip()


@dataclass(frozen=True)
class ParsedSource:
    source: SourceFile
    tree: Tree
    language_name: str


def parse_source(path: Path, defines: list[str]) -> ParsedSource:
    raw_text = path.read_text(encoding="utf-8")
    preprocessed = preprocess_source(raw_text, defines)
    source = SourceFile.from_text(path, preprocessed)
    parser, language_name = _build_parser(path)
    tree = parser.parse(source.text.encode("utf-8"))
    return ParsedSource(source=source, tree=tree, language_name=language_name)


def find_function(parsed: ParsedSource, name: str) -> Node:
    matches = [node for node in _iter_nodes(parsed.tree.root_node) if _is_function_named(node, parsed.source, name)]
    if not matches:
        raise CiftError(f"関数が見つかりません: {name}")
    if len(matches) > 1:
        raise CiftError(f"同名関数が複数見つかりました: {name}")
    return matches[0]


def function_body(function_node: Node) -> Node:
    for child in function_node.named_children:
        if child.type == "compound_statement":
            return child
    raise CiftError("関数本体を特定できません")


def node_text(source: SourceFile, node: Node) -> str:
    return source.text.encode("utf-8")[node.start_byte:node.end_byte].decode("utf-8")


def condition_text(source: SourceFile, node: Node) -> str:
    text = node_text(source, node)
    return text


def _build_parser(path: Path) -> tuple[Parser, str]:
    if path.suffix.lower() in CPP_EXTENSIONS:
        return Parser(Language(tree_sitter_cpp.language())), "cpp"
    return Parser(Language(tree_sitter_c.language())), "c"


def _iter_nodes(root: Node) -> list[Node]:
    nodes: list[Node] = []
    stack = [root]
    while stack:
        node = stack.pop()
        nodes.append(node)
        stack.extend(reversed(node.named_children))
    return nodes


def _is_function_named(node: Node, source: SourceFile, name: str) -> bool:
    if node.type != "function_definition":
        return False
    declarator = next(
        (child for child in node.named_children if child.type.endswith("declarator")),
        None,
    )
    if declarator is None:
        return False
    return _extract_declarator_name(source, declarator) == name


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
