from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from lark import Lark, Token, Tree

from . import astree


def index_of[T](it: Iterable[T], predicate: Callable[[T], bool], default: int = -1):
    return next((i for i, e in enumerate(it) if predicate(e)), default)


class TreeTransformer(ABC):
    source_position: astree.SourcePosition
    current_node: Tree

    def transform(self, node: Tree) -> Any:
        children = [
            self.transform(child) for child in node.children if isinstance(child, Tree)
        ]

        self.source_position = astree.SourcePosition(
            node.meta.line,
            node.meta.column,
            node.meta.end_line,
            node.meta.end_column,
        )

        handler = getattr(self, node.data)
        if not handler:
            raise NotImplementedError(f"Handler for {node.data} is not implemented")

        self.current_node = node

        return handler(*children)


class AstTransformer(TreeTransformer):
    def string(self):
        token: Token = self.current_node.children[0]
        value = token.value
        return astree.LiteralString(self.source_position, value[1:-1])

    def name(self):
        token: Token = self.current_node.children[0]
        name = token.value
        return astree.Name(self.source_position, name)

    def call(
        self,
        target: astree.Expression,
        args: tuple[list[astree.Expression], dict[str, astree.Expression]]
        | None = None,
    ):

        (pos_args, key_args) = args if args else ([], {})
        return astree.Call(self.source_position, target, pos_args, key_args)

    def call_args(self, *args: astree.Expression | tuple[str, astree.Expression]):
        args = [arg for arg in args if arg]
        first_kw_position = index_of(args, lambda a: isinstance(a, tuple), len(args))
        pos_args: list[astree.Expression] = args[0:first_kw_position]  # pyright: ignore[reportAssignmentType]
        key_args: list[tuple[str, astree.Expression]] = args[first_kw_position:]  # pyright: ignore[reportAssignmentType]
        return pos_args, dict(key_args)

    def kwarg(self, name: str, expr: astree.Expression):
        return (name, expr)

    def variable(self, name: astree.Name):
        return astree.Variable(self.source_position, name)

    def list(self, *items: astree.Expression):
        return astree.List(self.source_position, list(items))

    def list_comprehension(
        self,
        expression: astree.Expression,
        target: astree.Name,
        iterable: astree.Expression,
    ):
        return astree.ListComprehension(
            self.source_position, expression, target, iterable
        )

    def attributeref(self, expr: astree.Expression, name: astree.Name):
        return astree.AttributeRef(self.source_position, expr, name)

    def assignment(self, name: astree.Name, expression: astree.Expression):
        return (name, expression)

    def listing(self, *entries: tuple[astree.Name, astree.Expression]):
        assignments: dict[str, astree.Expression] = dict()
        for name, expression in entries:
            if name.name in assignments:
                raise RuntimeError(f"Name '{name}' is already assigned")
            assignments[name.name] = expression

        return assignments


__parser = Lark.open_from_package(
    __name__,
    "grammar.lark",
    start="listing",
    parser="lalr",
    propagate_positions=True,
)


def parse(source: str) -> Mapping[str, astree.Expression]:
    tree = __parser.parse(source)
    assignments: dict[str, astree.Expression] = AstTransformer().transform(tree)
    return assignments
