from abc import ABC, abstractmethod
from typing import Any

from .operation import Operation, OperationContext


class OperationContextFactory(ABC):
    @abstractmethod
    def create_context(self) -> OperationContext: ...


class OperationExecutor(ABC):
    @abstractmethod
    async def execute(self, operation: Operation) -> Any: ...
