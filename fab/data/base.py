from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
import pathlib
from typing import override


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


class Function(Object, ABC):
    @abstractmethod
    def call(self, args: list[Object], kwargs: dict[str, Object]) -> Object: ...
