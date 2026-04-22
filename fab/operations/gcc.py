import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any, override

from blake3 import blake3

from ..model import Operation, OperationContext
from ..util.hash_objects import hash_objects


class GccCompile(Operation):
    def __init__(self, source: Path, includes: Sequence[Path]):
        self.__source = source
        self.__includes = includes

    @override
    async def execute(self, context: OperationContext) -> Any:
        key = hash_objects(blake3(), "gcc_compile", self.__source)
        if context.cache_check(key):
            return context.cache_load_path(key)

        sandbox = context.get_sandbox()
        source_link = sandbox / self.__source.name
        source_link.symlink_to(self.__source.absolute())

        outputname = self.__source.with_suffix(".o").name

        cmd = [
            "gcc",
            "-c",
            *[f"-I {str(p.absolute())}" for p in self.__includes],
            "-o",
            outputname,
            str(source_link.name),
        ]
        print(cmd)

        result = await asyncio.create_subprocess_shell(" ".join(cmd), cwd=sandbox)
        returncode = await result.wait()

        if returncode != 0:
            exit(1)

        cached_path = context.cache_store_path(key, sandbox / outputname)
        return cached_path


class GccLink(Operation):
    def __init__(self, outputname: str, objects: Sequence[Path]):
        self.__outputname = outputname
        self.__objects = objects

    @override
    async def execute(self, context: OperationContext) -> Any:
        key = hash_objects(blake3(), "gcc_link", self.__objects)
        if context.cache_check(key):
            return context.cache_load_path(key)

        sandbox = context.get_sandbox()

        cmd = [
            "gcc",
            "-o",
            self.__outputname,
            *(str(p.absolute()) for p in self.__objects),
        ]
        print(cmd)

        result = await asyncio.create_subprocess_shell(" ".join(cmd), cwd=sandbox)
        returncode = await result.wait()

        if returncode != 0:
            exit(1)

        cached_path = context.cache_store_path(key, sandbox / self.__outputname)
        return cached_path
