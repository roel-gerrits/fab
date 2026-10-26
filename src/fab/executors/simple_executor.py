from typing import Any, override
from fab.model import Operation, OperationExecutor
from fab.model.executor import OperationContextFactory


class SimpleOperationExecutor(OperationExecutor):
    def __init__(self, context_factory: OperationContextFactory):
        self.__context_factory = context_factory

    @override
    async def execute(self, operation: Operation) -> Any:
        context = self.__context_factory.create_context()
        result = await operation.execute(context)
        context.cleanup()
        return result
