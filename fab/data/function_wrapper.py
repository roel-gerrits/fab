from .base import Object, Function
from typing import override


class WrappingFunction(Function):
    def __init__(self, func) -> None:
        self.__func = func

    @override
    def call(self, args: list[Object], kwargs: dict[str, Object]) -> Object:
        return self.__func(*args, **kwargs)
