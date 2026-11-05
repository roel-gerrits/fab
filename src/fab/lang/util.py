import itertools
import pathlib
import inspect
from abc import ABC
from collections.abc import Mapping, Sequence, Callable
from typing import override

from .data import EvaluationContext, Function, Object, FunctionCallError


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


def parse_args[T: tuple[type[Object], ...]](args: list[Object], types: T) -> T:

    for num, (arg, arg_type) in enumerate(itertools.zip_longest(args, types), 1):
        if arg is None:
            raise FunctionCallError(f"Argument {num} is missing.")
        if arg_type is None:
            raise FunctionCallError(f"Did not expect argument {num}.")
        if type(arg) != arg_type:
            raise FunctionCallError(
                f"Argument {num} must be of type {arg_type.__name__}, got {type(arg).__name__} instead."
            )

    return tuple(args)  # ty: ignore[invalid-return-type]


def wrap_into_function_class(f):
    parameters = list(inspect.signature(f).parameters.values())
    if len(parameters) < 1 or parameters[0].annotation != EvaluationContext:
        raise TypeError(f"First argument must be of type {EvaluationContext}")

    arg_types = [p.annotation for p in parameters[1:]]

    class FunctionImpl(Function):
        async def call(
            self,
            context: EvaluationContext,
            args: list[Object],
            kwargs: dict[str, Object],
        ) -> Object:

            validated_args = parse_args(args, tuple(arg_types))

            return f(context, *validated_args)

    return FunctionImpl
