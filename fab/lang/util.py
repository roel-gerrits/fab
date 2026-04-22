from abc import ABC
from collections.abc import Mapping, Sequence
import pathlib
from typing import override
from .data import Object, Function, EvaluationContext


class DictObject(Object):
    def __init__(self, contents: dict[str, Object]):
        self.__contents = contents

    @override
    def has_attr(self, name: str) -> bool:
        return name in self.__contents

    @override
    async def get_attr(self, name: str) -> Object:
        return self.__contents[name]

    @override
    def attrs(self) -> Sequence[str]:
        return list(self.__contents.keys())


class SimpleFunction(Function):
    def __init__(self, func) -> None:
        self.__func = func

    @override
    async def call(
        self, context: EvaluationContext, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        return self.__func(*args, **kwargs)


class BaseEvaluationContext(EvaluationContext, ABC):
    def __init__(
        self, initial_file: pathlib.Path, buildins: Mapping[str, Object]
    ) -> None:
        self.__current_file = initial_file
        self.__buildins = buildins

    @override
    def apply_filename(self, path: pathlib.Path):
        self.__current_file = self.__current_file.parent.joinpath(path)

    @override
    def get_current_file(self) -> pathlib.Path:
        return self.__current_file

    @property
    @override
    def buildins(self) -> Mapping[str, Object]:
        return self.__buildins
