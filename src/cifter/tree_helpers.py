from __future__ import annotations

from tree_sitter import Node


def container_statements(container: Node) -> list[Node]:
    if container.type == "compound_statement":
        return list(container.named_children)
    if container.type == "case_statement":
        return [child for child in container.named_children if is_body_statement(child)]
    if container.type == "labeled_statement":
        return [container.named_children[-1]]
    return [container]


def is_body_statement(node: Node) -> bool:
    return node.type.endswith("_statement") or node.type == "declaration"


def case_body_container(case_node: Node) -> Node:
    for child in case_node.named_children:
        if child.type == "compound_statement":
            return child
    return case_node


def else_clause(if_node: Node) -> Node | None:
    for child in if_node.named_children:
        if child.type == "else_clause":
            return child
    return None


def is_branching_statement(node: Node) -> bool:
    return node.type in {"if_statement", "switch_statement", "for_statement", "while_statement", "do_statement"}


def is_function_body(node: Node) -> bool:
    return node.type == "compound_statement" and node.parent is not None and node.parent.type == "function_definition"
