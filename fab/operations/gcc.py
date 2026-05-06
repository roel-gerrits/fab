import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, override

from blake3 import blake3

from fab.lang import data


from ..model import Operation, OperationContext, GlobalState
from ..util.hash_objects import hash_objects


@dataclass
class CompileObject:
    file: Path
    arguments: list[str]


class CompileCommandsCollector(GlobalState):
    def __init__(self, context: OperationContext) -> None:
        self.__commands: list[CompileObject] = []

    def add_compile_object(self, obj: CompileObject):
        self.__commands.append(obj)

    def get_compile_commands(self) -> list[CompileObject]:
        return self.__commands

    # @override
    # def done(self):
    #     if not self.__do_collect:
    #         return
    #
    #     with open("compile_commands.json", "w") as f:
    #         json.dump(
    #             [
    #                 {
    #                     "file": str(obj.file),
    #                     "arguments": obj.arguments,
    #                     "output": str(obj.output),
    #                 }
    #                 for obj in self.__commands
    #             ],
    #             f,
    #             indent=4,
    #         )
    #


def flatten(lst: list[Any]) -> list[Any]:
    result = list()
    for item in lst:
        if isinstance(item, list):
            for subitem in item:
                result.append(subitem)
        else:
            result.append(item)
    return result


class GccCompile(Operation):
    def __init__(self, source: Path, includes: Sequence[Path]):
        self.__source = source
        self.__includes = includes

    @override
    async def execute(self, context: OperationContext) -> Any:

        context.get_global_state(CompileCommandsCollector).add_compile_object(
            CompileObject(
                file=self.__source.absolute(),
                arguments=[
                    "g++",
                    "-c",
                    *flatten([["-I", str(p.absolute())] for p in self.__includes]),
                    str(self.__source.name),
                ],
            )
        )

        key = hash_objects(blake3(), "g++_compile", self.__source)
        if context.cache_check(key):
            return context.cache_load_path(key)

        sandbox = context.get_sandbox()
        source_link = sandbox / self.__source.name
        source_link.symlink_to(self.__source.absolute())

        outputname = self.__source.with_suffix(".o").name

        cmd = [
            "g++",
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
        key = hash_objects(blake3(), "g++_link", self.__objects)
        if context.cache_check(key):
            return context.cache_load_path(key)

        sandbox = context.get_sandbox()

        cmd = [
            "g++",
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


class GccCollectCompileCommands(Operation):
    @override
    async def execute(self, context: OperationContext) -> Any:
        compile_commands = context.get_global_state(
            CompileCommandsCollector
        ).get_compile_commands()

        sandbox = context.get_sandbox()
        compile_commands_file = sandbox / "compile_commands.json"
        with open(compile_commands_file, "w") as f:
            json.dump(
                [
                    {
                        "directory": str(obj.file.parent),
                        "file": str(obj.file),
                        "arguments": obj.arguments,
                    }
                    for obj in compile_commands
                ],
                f,
                indent=4,
            )

        return compile_commands_file
