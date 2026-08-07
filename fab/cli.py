"""Fabulous builder.

Usage:
    fab [options] (do|run|ls|tree) <target> [--file FILE] [--no-cache] [--no-remote-cache]
    fab [options] list-targets [--file FILE]
    fab [options] clean-containers
    fab [options] clean-cache
    fab [options] cache-info
    fab --version

Options:
    -h, --help            Show this helpful text.
    -v, --version         Show version.
    -f FILE, --file FILE  Build file to read. [default: build.fab]
    --no-cache            Do not use cache.
    --no-remote-cache     Do not use remote cache.

"""

import asyncio
import subprocess
from typing import Any, override
from docopt import docopt
from pathlib import Path
from xdg_base_dirs import xdg_data_home
import tempfile

from fab.oci.container_admin import ContainerAdmin
from fab.oci.podman import PodmanClient


from .lang.data import List, Object, PathObj
from .caching import DiskCache, CacheHitCounter
from .executors.simple_executor import SimpleOperationExecutor
from .lang.evaluation_context import DefaultEvaluationContext
from .lang.evaluator import EvaluationError, evaluate_context
from .model import (
    Cache,
    CommandFailedError,
    OperationContext,
    OciContainer,
    OperationError,
    StreamType,
)
from .model.executor import OperationContextFactory


class MainOperationContextFactory(OperationContextFactory):
    def __init__(
        self, cache: Cache, sandbox_root: Path, container_admin: ContainerAdmin
    ):
        self._cache: Cache = cache
        self._global_state: dict[type, object] = dict()
        self._sandbox_root: Path = sandbox_root
        self._sandbox_root.mkdir(parents=True, exist_ok=True)
        self._container_admin: ContainerAdmin = container_admin

    @override
    def create_context(self) -> OperationContext:
        this = self

        class Impl(OperationContext):
            def __init__(self):
                self.sandboxes: list[Path] = list()

            @override
            def get_sandbox(self) -> Path:
                sandbox = Path(tempfile.mkdtemp(dir=this._sandbox_root))
                self.sandboxes.append(sandbox)
                return sandbox

            @override
            async def get_oci_container(
                self,
                image: str,
                working_dir: str | None = None,
                cmd: list[str] | None = None,
                user: str | None = None,
                host_mountpoint: Path | None = None,
            ) -> OciContainer:
                return await this._container_admin.get_container(
                    image,
                    working_dir,
                    cmd,
                    user,
                    [("/", str(host_mountpoint))] if host_mountpoint else None,
                )

            @override
            def report_progress(self):
                raise NotImplementedError()

            @override
            async def cache_check(self, key: bytes) -> bool:
                return await this._cache.has(key)

            @override
            async def cache_load_path(self, key: bytes) -> Path:
                return await this._cache.get_path(key)

            @override
            async def cache_store_path(self, key: bytes, path: Path) -> Path:
                return await this._cache.store_path(key, path)

            @override
            def get_param(self, key: str) -> Any:
                raise NotImplementedError()

            @override
            def get_global_state[T](self, state_class: type[T]) -> T:
                if state_class not in this._global_state:
                    this._global_state[state_class] = state_class()
                assert isinstance(this._global_state[state_class], state_class)
                return this._global_state[state_class]

            @override
            def cleanup(self):
                pass

        return Impl()


def print_result(result: Object):
    if isinstance(result, PathObj):
        print(result.path)
    elif isinstance(result, List):
        print("list:")
        for item in result.items:
            if isinstance(item, PathObj):
                print(f"  {item.path}")


def format_evaluation_error(error: EvaluationError) -> str:
    source_file = error.context.get_current_file()
    source_position = error.expr.source_position
    source_line = source_file.read_text().splitlines()[source_position.start_line - 1]

    output: list[str] = []
    output.append(f'File "{source_file}", line {source_position.start_line}:\n')
    output.append("  ")
    output.append(source_line)
    output.append("\n")
    output.append("  ")
    output.append(" " * (source_position.start_column - 1))
    output.append("^" * (source_position.end_column - source_position.start_column))
    output.append("\n")

    if isinstance(error.cause, CommandFailedError):
        output.append(f"Command failed, exitcode={error.cause.exitcode}\n")
        output.append("  ")
        output.append(" ".join(error.cause.cmd))
        output.append("\n")
        output.append("\n")

        for chunk in error.cause.output:
            output.append(chunk.chunk.decode())

    return "".join(output)


async def cli():
    data_home = xdg_data_home() / "fab"
    args: dict[str, str] = docopt(__doc__)
    # print(args)

    # disk_cache = HitCounter(DiskCache(...))
    # remote_cache = HitCounter(RemoteCache(...))
    # combi_cache = ChainedCache(disk_cache, remote_cache)
    cache = CacheHitCounter(DiskCache(data_home / "cache"))

    # ui = Tui(disk_cache_counter, remote_cache_counter)

    podman_client = PodmanClient()
    container_admin = ContainerAdmin(podman_client)
    # oci_container_admin = OciContainerAdmin(...)
    #
    # sandbox_admin = SandboxAdmin(...)

    operation_context_factory = MainOperationContextFactory(
        cache,
        data_home / "sandbox",
        container_admin,
    )

    operation_executor = SimpleOperationExecutor(operation_context_factory)

    evaluation_context = DefaultEvaluationContext(
        Path(args["--file"]),
        operation_executor,
    )

    target: str = args["<target>"]

    async def evaluate_target():
        try:
            eval_result = evaluate_context(evaluation_context)
            result = await eval_result.get_attr(target)
            print(f"Cache stats: {cache.hits} hits, {cache.misses} misses")
        except EvaluationError as e:
            print(format_evaluation_error(e))
            return None
        return result

    async def do():
        result = await evaluate_target()
        print_result(result)

    async def run():
        result = await evaluate_target()
        if not isinstance(result, PathObj):
            print(f"Target '{target}' does not evaluate to a Path")
            exit(1)

        subprocess.run(result.path)

    def list_targets():
        build_object = evaluate_context(evaluation_context)
        for name in build_object.attrs():
            print(name)

    async def clean_containers():
        count = await container_admin.clean_containers()
        print(f"Removed {count} container(s).")

    if args["list-targets"]:
        list_targets()
    elif args["clean-containers"]:
        await clean_containers()
    elif args["do"]:
        await do()
    elif args["run"]:
        await run()
    else:
        print(args)

    await podman_client.aclose()


def main():
    asyncio.run(cli())


if __name__ == "__main__":
    main()
