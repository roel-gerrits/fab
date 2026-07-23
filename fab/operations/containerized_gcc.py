from collections.abc import Sequence
from pathlib import Path
from typing import override

from blake3 import blake3
from .gcc import CompileCommandsCollector, CompileObject
from ..util.hash_objects import hash_objects
from ..model import Operation, OperationContext, OperationError


from ..util.flatten_list import flatten


class ContainerizedSandbox:
    def __init__(self, context: OperationContext, oci_image: str) -> None:
        self.__context = context
        self.__image = oci_image

        self.__sandbox = context.get_sandbox()
        self.__host_mountpoint = Path("/host_root")

    def inject(self, host_path: Path) -> Path:
        link = self.__sandbox / host_path.name
        link.symlink_to(self.translate(host_path))
        return link.relative_to(self.__sandbox)

    def translate(self, host_path: Path) -> Path:
        return self.__host_mountpoint / host_path.absolute().relative_to(Path("/"))

    async def execute(self, cmd: list[str]):
        print(cmd)
        container = await self.__context.get_oci_container(
            image=self.__image,
            user="root",
            host_mountpoint=self.__host_mountpoint,
        )
        return await container.exec(cmd, str(self.translate(self.__sandbox)))

    async def execute_and_check(self, cmd: list[str]):
        process, output = await self.execute(cmd)
        async for chunk in output:
            print(chunk, end=None, flush=True)
        exit_code = await process.wait()
        if exit_code != 0:
            raise OperationError("Operation exited with non-zero code")

    def extract(self, path: Path | str) -> Path:
        return self.__sandbox / Path(path)


class GccCompile(Operation):
    def __init__(
        self,
        oci_image: str,
        target_triplet: str | None,
        source: Path,
        includes: Sequence[Path],
    ) -> None:
        self.__oci_image = oci_image
        self.__target_triplet = target_triplet
        self.__source = source
        self.__includes = includes

    @override
    async def execute(self, context: OperationContext) -> Path:
        key = hash_objects(
            blake3(),
            type(self).__qualname__,
            self.__oci_image,
            self.__target_triplet,
            self.__source,
            self.__includes,
        )

        if context.cache_check(key):
            return context.cache_load_path(key)

        gcc_bin = f"{self.__target_triplet}-g++" if self.__target_triplet else "g++"
        sandbox = ContainerizedSandbox(context, self.__oci_image)
        source = sandbox.inject(self.__source)
        includes = [sandbox.translate(include) for include in self.__includes]
        outputname = self.__source.name + ".o"

        context.get_global_state(CompileCommandsCollector).add_compile_object(
            CompileObject(
                file=self.__source.absolute(),
                arguments=flatten(
                    [
                        "g++",
                        "-c",
                        [
                            ["-I", str(include.absolute())]
                            for include in self.__includes
                        ],
                        "-o",
                        outputname,
                        str(source),
                    ]
                ),
            )
        )

        cmd = flatten(
            [
                gcc_bin,
                "-c",
                [["-I", str(include)] for include in includes],
                "-o",
                outputname,
                str(source),
            ]
        )

        await sandbox.execute_and_check(cmd)

        result = sandbox.extract(outputname)

        return context.cache_store_path(key, result)


class GccLink(Operation):
    def __init__(
        self,
        oci_image: str,
        target_triplet: str | None,
        outputname: str,
        objects: Sequence[Path],
    ) -> None:
        self.__oci_image = oci_image
        self.__target_triplet = target_triplet
        self.__outputname = outputname
        self.__objects = objects

    @override
    async def execute(self, context: OperationContext) -> Path:
        key = hash_objects(
            blake3(),
            type(self).__qualname__,
            self.__oci_image,
            self.__target_triplet,
            self.__outputname,
            self.__objects,
        )

        if context.cache_check(key):
            return context.cache_load_path(key)

        gcc_bin = f"{self.__target_triplet}-g++" if self.__target_triplet else "g++"
        sandbox = ContainerizedSandbox(context, self.__oci_image)
        objects = [sandbox.translate(object) for object in self.__objects]

        cmd = flatten([gcc_bin, "-o", self.__outputname, [str(obj) for obj in objects]])

        await sandbox.execute_and_check(cmd)

        result = sandbox.extract(self.__outputname)

        return context.cache_store_path(key, result)
