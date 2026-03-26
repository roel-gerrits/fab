from typing import override
from .operation import Operation, Context
from .base import Object


class WrappingOperation(Operation):
    def __init__(self, func) -> None:
        self.__func = func

    @override
    async def execute(
        self, context: Context, args: list[Object], kwargs: dict[str, Object]
    ) -> Object:
        return await self.__func(context, *args, *kwargs)
