from __future__ import annotations

import pathlib
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, override

from ..model import Operation


class Object(ABC):
    def has_attr(self, name: str) -> bool:
        return False

    def attrs(self) -> Sequence[str]:
        return []

    async def get_attr(self, name: str) -> Object:
        raise KeyError

    @override
    def __eq__(self, value: object, /) -> bool:
        raise NotImplementedError


class String(Object):
    value: str

    def __init__(self, value: str) -> None:
        self.value = value

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, String):
            return False
        return self.value == other.value

    @override
    def __repr__(self) -> str:
        return f'<String "{self.value}">'


class List(Object):
    items: Sequence[Object]

    def __init__(self, items: Sequence[Object]) -> None:
        self.items = items

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, List):
            return False
        return self.items == other.items


class PathObj(Object):
    path: pathlib.Path

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, PathObj):
            return False
        return self.path == other.path


class EvaluationContext(ABC):
    @abstractmethod
    def apply_filename(self, path: pathlib.Path) -> None: ...

    @abstractmethod
    def get_current_file(self) -> pathlib.Path: ...

    @abstractmethod
    async def execute_operation(self, operation: Operation) -> Any: ...

    @property
    @abstractmethod
    def buildins(self) -> Mapping[str, Object]: ...


class Function(Object, ABC):
    @abstractmethod
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object: ...
