from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence

from lark import Lark, Token, visitors

from . import astree


def index_of[T](it: Iterable[T], predicate: Callable[[T], bool], default: int = -1):
    return next((i for i, e in enumerate(it) if predicate(e)), default)


class Transformer(visitors.Transformer):
    def string(self, args: tuple[Token]):
        (value,) = args
        return astree.LiteralString(value[1:-1])

    def name(self, args: tuple[Token]):
        name = str(args[0].value)
        return astree.Name(name)

    def call(
        self,
        args: tuple[
            astree.Expression,
            tuple[list[astree.Expression], dict[str, astree.Expression]] | None,
        ],
    ):
        target = args[0]

        (pos_args, key_args) = args[1] if args[1] else ([], {})
        return astree.Call(target, pos_args, key_args)

    def call_args(
        self, args: Sequence[astree.Expression | tuple[str, astree.Expression]]
    ):
        args = [arg for arg in args if arg]
        first_kw_position = index_of(args, lambda a: isinstance(a, tuple), len(args))
        pos_args: list[astree.Expression] = args[0:first_kw_position]  # pyright: ignore[reportAssignmentType]
        key_args: list[tuple[str, astree.Expression]] = args[first_kw_position:]  # pyright: ignore[reportAssignmentType]
        return pos_args, dict(key_args)

    def kwarg(self, args: tuple[str, astree.Expression]):
        return (args[0], args[1])

    def variable(self, args: tuple[astree.Name]):
        (name,) = args
        return astree.Variable(name)

    def list(self, args: list[astree.Expression]):
        return astree.List(args)

    def attributeref(self, args: tuple[astree.Expression, astree.Name]):
        expr, name = args
        return astree.AttributeRef(expr, name)

    def assignment(self, args: tuple[str, astree.Expression]):
        name, expression = args
        return (name, expression)

    def listing(self, args: list[tuple[astree.Name, astree.Expression]]):
        assignments: dict[str, astree.Expression] = dict()
        for name, expression in args:
            if name.name in assignments:
                raise RuntimeError(f"Name '{name}' is already assigned")
            assignments[name.name] = expression

        return assignments


__parser = Lark.open_from_package(
    __name__,
    "grammar.lark",
    start="listing",
    parser="lalr",
    transformer=Transformer(),
)


def parse(source: str) -> Mapping[str, astree.Expression]:
    assignments: dict[str, astree.Expression] = __parser.parse(source)
    return assignments
