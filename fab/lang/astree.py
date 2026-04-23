import abc
from math import exp
from typing import override


class AstNode(abc.ABC):
    pass


class Name(AstNode):
    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @override
    def __repr__(self) -> str:
        return f"<Name {self.name}>"

    @override
    def __str__(self) -> str:
        return self.name


class Expression(AstNode, abc.ABC):
    pass


class LiteralString(Expression):
    value: str

    def __init__(self, value: str) -> None:
        self.value = value

    @override
    def __repr__(self):
        return f'<LiteralString "{self.value}">'


class Call(Expression):
    target: Expression
    pos_args: list[Expression]
    key_args: dict[Name, Expression]

    def __init__(
        self,
        target: Expression,
        pos_args: list[Expression],
        key_args: dict[Name, Expression],
    ) -> None:
        self.target = target
        self.pos_args = pos_args
        self.key_args = key_args

    @override
    def __repr__(self) -> str:
        return (
            f"<Call target={self.target}, args={self.pos_args}, kwargs={self.key_args}>"
        )


class Variable(Expression):
    name: Name

    def __init__(self, name: Name) -> None:
        self.name = name

    @override
    def __repr__(self) -> str:
        return f"<Variable {self.name}>"


class List(Expression):
    items: list[Expression]

    def __init__(self, items: list[Expression]) -> None:
        self.items = items

    @override
    def __repr__(self):
        return f"<List {','.join((str(x) for x in self.items))}>"


class ListComprehension(Expression):
    expression: Expression
    target: Name
    iterable: Expression

    def __init__(self, expression: Expression, target: Name, iterable: Expression):
        self.expression = expression
        self.target = target
        self.iterable = iterable

    @override
    def __repr__(self) -> str:
        return f"<ListComprehension ...>"


class AttributeRef(Expression):
    target: Expression
    name: Name

    def __init__(self, target: Expression, name: Name) -> None:
        self.target = target
        self.name = name

    @override
    def __repr__(self) -> str:
        return f"<AttributeRef {self.target}.{self.name}>"
