import abc
from typing import override


class SourcePosition:
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    def __init__(
        self, start_line: int, start_column: int, end_line: int = 0, end_column: int = 0
    ) -> None:
        self.start_line = start_line
        self.start_column = start_column
        self.end_line = end_line
        self.end_column = end_column

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, SourcePosition):
            return False
        return (
            self.start_line == other.start_line
            and self.start_column == other.start_column
            and self.end_line == other.end_line
            and self.end_column == other.end_column
        )

    def __str__(self):
        return (
            f"{self.start_line}:{self.start_column}-{self.end_line}:{self.end_column}"
        )


class AstNode(abc.ABC):
    source_position: SourcePosition

    def __init__(self, source_position: SourcePosition) -> None:
        self.source_position = source_position


class Name(AstNode):
    name: str

    def __init__(self, source_position: SourcePosition, name: str) -> None:
        super().__init__(source_position)
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

    def __init__(self, source_position: SourcePosition, value: str) -> None:
        super().__init__(source_position)
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
        source_position: SourcePosition,
        target: Expression,
        pos_args: list[Expression],
        key_args: dict[Name, Expression],
    ) -> None:
        super().__init__(source_position)
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

    def __init__(self, source_position: SourcePosition, name: Name) -> None:
        super().__init__(source_position)
        self.name = name

    @override
    def __repr__(self) -> str:
        return f"<Variable {self.name}>"


class List(Expression):
    items: list[Expression]

    def __init__(
        self, source_position: SourcePosition, items: list[Expression]
    ) -> None:
        super().__init__(source_position)
        self.items = items

    @override
    def __repr__(self):
        return f"<List {','.join((str(x) for x in self.items))}>"


class ListComprehension(Expression):
    expression: Expression
    target: Name
    iterable: Expression

    def __init__(
        self,
        source_position: SourcePosition,
        expression: Expression,
        target: Name,
        iterable: Expression,
    ):
        super().__init__(source_position)
        self.expression = expression
        self.target = target
        self.iterable = iterable

    @override
    def __repr__(self) -> str:
        return f"<ListComprehension ...>"


class AttributeRef(Expression):
    target: Expression
    name: Name

    def __init__(
        self, source_position: SourcePosition, target: Expression, name: Name
    ) -> None:
        super().__init__(source_position)
        self.target = target
        self.name = name

    @override
    def __repr__(self) -> str:
        return f"<AttributeRef {self.target}.{self.name}>"
