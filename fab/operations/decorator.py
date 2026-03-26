from collections.abc import Callable
from typing import override

from ..building import Context
from ..data.base import Object
from ..data.operation import Operation


def operation(f: Callable) -> Operation:

    class Operation_(Operation):
        @override
        async def execute(
            self, context: Context, args: list[Object], kwargs: dict[str, Object]
        ) -> Object:
            return await f(context, *args, **kwargs)

    return Operation_()
