from abc import ABC, abstractmethod

from .operation import Operation


class OperationExecutor(ABC):
    @abstractmethod
    async def execute(self, operation: Operation): ...
