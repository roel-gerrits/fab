from collections.abc import Mapping
import pathlib
from typing import Any, override

from ..lang.data import EvaluationContext, Object

from ..model import Operation, OperationExecutor

from ..lang.buildins import (
    GccCompileFunc,
    GccLinkFunc,
    GccCollectCompileCommandsFunc,
    LoadFunc,
    PathFunc,
    LinkFunc,
    HttpGetFunc,
    ExtractFunc,
    HttpArchiveFunc,
    ContainerizedGcc,
)

buildins = {
    "load": LoadFunc(),
    "path": PathFunc(),
    "link": LinkFunc(),
    "http_get": HttpGetFunc(),
    "extract": ExtractFunc(),
    "http_archive": HttpArchiveFunc(),
    "gcc_compile": GccCompileFunc(),
    "gcc_link": GccLinkFunc(),
    "gcc_collect_compile_commands": GccCollectCompileCommandsFunc(),
    "containerized_gcc": ContainerizedGcc(),
}


class DefaultEvaluationContext(EvaluationContext):
    def __init__(
        self, initial_file: pathlib.Path, operation_executor: OperationExecutor
    ) -> None:
        self.__operation_executor: OperationExecutor = operation_executor
        self.__current_file = initial_file
        self.__buildins = buildins

    @override
    async def execute_operation(self, operation: Operation) -> Any:
        return await self.__operation_executor.execute(operation)

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
