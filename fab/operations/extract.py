from pathlib import Path
from typing import Any, override

from blake3 import blake3

from ..model import Operation, OperationContext
from ..util.hash_objects import hash_objects

import shutil


class Extract(Operation):
    def __init__(self, archive: Path) -> None:
        self.__archive = archive

    @override
    async def execute(self, context: OperationContext) -> Any:
        key = hash_objects(blake3(), "Extract", self.__archive)

        if context.cache_check(key):
            return context.cache_load_path(key)

        sandbox = context.get_sandbox()
        extract_dir = sandbox / self.__archive.name
        extract_dir.mkdir()

        shutil.unpack_archive(self.__archive, extract_dir)

        cached_path = context.cache_store_path(key, extract_dir)

        return cached_path
