from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import override

from blake3 import blake3


from ..model import Operation, OperationContext, CommandFailedError
from ..util.flatten_list import flatten
from ..util.hash_objects import hash_objects
from .gcc import CompileCommandsCollector, CompileObject


class ContainerizedSandbox:
    def __init__(self, context: OperationContext, oci_image: str) -> None:
        self.__context = context
        self.__image = oci_image

        self.__sandbox = context.get_sandbox()
        self.__host_mountpoint = Path("/host_root")

    def inject(self, host_path: Path) -> Path:
        link = self.__sandbox / host_path.name
        link.symlink_to(self.translate_host_to_sandbox(host_path))
        return link.relative_to(self.__sandbox)

    def translate_host_to_sandbox(self, host_path: Path) -> Path:
        return self.__host_mountpoint / host_path.absolute().relative_to(Path("/"))

    def translate_sandbox_to_host(self, sandbox_path: Path) -> Path:
        return Path("/") / sandbox_path.absolute().relative_to(self.__host_mountpoint)

    async def execute(self, cmd: list[str]):
        container = await self.__context.get_oci_container(
            image=self.__image,
            user="root",
            host_mountpoint=self.__host_mountpoint,
        )
        return await container.exec(
            cmd, str(self.translate_host_to_sandbox(self.__sandbox))
        )

    async def execute_and_check(self, cmd: list[str]):
        process, output_stream = await self.execute(cmd)
        output = [chunk async for chunk in output_stream]
        exit_code = await process.wait()
        if exit_code != 0:
            raise CommandFailedError(cmd, exit_code, output)

    def extract(self, path: Path | str) -> Path:
        return self.__sandbox / Path(path)


def _parse_make_deps(inp: str) -> Iterable[Path]:
    it = iter(inp)

    def read_token():
        token = ""
        while c := next(it, None):
            if c == "\\":
                c = next(it)
                if c != "\n":
                    token += c
                continue

            if c == " ":
                if token:
                    return token

            else:
                token += c

        if token:
            return token

    read_token()  # skip target
    read_token()  # skip main file
    while t := read_token():
        yield Path(t.strip())


def _parse_deps_file(deps_file: Path) -> list[Path]:
    return list(_parse_make_deps(deps_file.read_text()))


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
        gcc_bin = f"{self.__target_triplet}-g++" if self.__target_triplet else "g++"
        sandbox = ContainerizedSandbox(context, self.__oci_image)
        source = sandbox.inject(self.__source)
        includes = [
            sandbox.translate_host_to_sandbox(include) for include in self.__includes
        ]
        outputname = self.__source.name + ".o"

        context.get_global_state(CompileCommandsCollector).add_compile_object(
            CompileObject(
                file=self.__source.absolute(),
                arguments=flatten(
                    [
                        gcc_bin,
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

        deps_key = hash_objects(
            blake3(),
            type(self).__qualname__,
            self.__oci_image,
            self.__target_triplet,
            self.__source,
            [str(p) for p in self.__includes],
        )

        deps_cached = await context.cache_check(deps_key)

        if deps_cached:
            deps_file = await context.cache_load_path(deps_key)
            dep_paths = _parse_deps_file(deps_file)

            key = hash_objects(
                blake3(),
                type(self).__qualname__,
                self.__oci_image,
                self.__target_triplet,
                self.__source,
                [sandbox.translate_sandbox_to_host(p) for p in dep_paths],
            )

            if await context.cache_check(key):
                return await context.cache_load_path(key)

        cmd = flatten(
            [
                gcc_bin,
                "-c",
                [["-I", str(include)] for include in includes],
                "-o",
                outputname,
                "-MMD",
                "-MF",
                "deps.d",
                str(source),
            ]
        )

        await sandbox.execute_and_check(cmd)

        if not deps_cached:
            deps_file = sandbox.extract("deps.d")
            deps_file = await context.cache_store_path(deps_key, deps_file)

        outfile = sandbox.extract(outputname)

        key = hash_objects(
            blake3(),
            type(self).__qualname__,
            self.__oci_image,
            self.__target_triplet,
            self.__source,
            [sandbox.translate_sandbox_to_host(p) for p in _parse_deps_file(deps_file)],
        )

        return await context.cache_store_path(key, outfile)


class GccLink(Operation):
    def __init__(
        self,
        oci_image: str,
        target_triplet: str | None,
        outputname: str,
        objects: Sequence[Path],
        options: Sequence[str] = (),
    ) -> None:
        self.__oci_image = oci_image
        self.__target_triplet = target_triplet
        self.__outputname = outputname
        self.__objects = objects
        self.__options = options

    @override
    async def execute(self, context: OperationContext) -> Path:
        key = hash_objects(
            blake3(),
            type(self).__qualname__,
            self.__oci_image,
            self.__target_triplet,
            self.__outputname,
            self.__objects,
            self.__options,
        )

        if await context.cache_check(key):
            return await context.cache_load_path(key)

        gcc_bin = f"{self.__target_triplet}-g++" if self.__target_triplet else "g++"
        sandbox = ContainerizedSandbox(context, self.__oci_image)
        objects = [
            sandbox.translate_host_to_sandbox(object) for object in self.__objects
        ]

        cmd = flatten(
            [
                gcc_bin,
                "-o",
                self.__outputname,
                [str(obj) for obj in objects],
                list(self.__options),
            ]
        )

        await sandbox.execute_and_check(cmd)

        result = sandbox.extract(self.__outputname)

        return await context.cache_store_path(key, result)
