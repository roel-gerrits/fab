from typing import Any, override

from ..model import Operation, OperationContext
from .extract import Extract
from .http_get import HttpGet


class HttpArchive(Operation):
    def __init__(self, url: str):
        self.__url = url

    @override
    async def execute(self, context: OperationContext) -> Any:
        http_get = HttpGet(self.__url)
        archive = await http_get.execute(context)

        extract = Extract(archive)
        result = await extract.execute(context)

        return result
