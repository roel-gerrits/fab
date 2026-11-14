from __future__ import annotations

import pathlib
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, override

from ..model import Error, Operation


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


class ObjectWithMethods(Object):
    def __init__(self):
        self.__methods: dict[str, Function] = {}

    def add_method(self, name: str, func: Function):
        assert name not in self.__methods
        self.__methods[name] = func

    def has_attr(self, name: str) -> bool:
        return name in self.__methods

    def attrs(self) -> Sequence[str]:
        return list(self.__methods.keys())

    async def get_attr(self, name: str) -> Object:
        return self.__methods[name]


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


class FunctionCallError(Error):
    pass


class Function(Object, ABC):
    @abstractmethod
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object: ...
