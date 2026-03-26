from __future__ import annotations

from abc import ABC, abstractmethod

from .base import Object
from ..building import Context


class Operation(Object, ABC):
    @abstractmethod
    async def execute(
        self, context: Context, args: list[Object], kwargs: dict[str, Object]
    ) -> Object: ...
