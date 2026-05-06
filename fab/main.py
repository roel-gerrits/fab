import argparse
import asyncio
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, override

from .caching import DiskCache
from .lang.util import BaseEvaluationContext
from .lang.buildins import (
    GccCompileFunc,
    GccLinkFunc,
    GccCollectCompileCommandsFunc,
    LoadFunc,
    PathFunc,
    LinkFunc,
    HttpGetFunc,
    ExtractFunc,
    HttpArchiveFunc,
)
from .model import GlobalState, Operation, OperationContext
from .lang.evaluator import evaluate_context


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", default="build.txt", type=Path)

    subparsers = parser.add_subparsers()

    do_parser = subparsers.add_parser("do")
    do_parser.add_argument("target", nargs="?", type=str)

    async def main():
        args = parser.parse_args()

        sandboxes = Path(".sandboxes")
        sandboxes.mkdir(parents=True, exist_ok=True)

        cache = DiskCache(Path(".cache"))

        global_state: dict[type[GlobalState], GlobalState] = dict()

        class BasicOperationContext(OperationContext):
            @override
            def get_sandbox(self) -> Path:
                sandbox = Path(mkdtemp(dir=sandboxes))
                return sandbox

            @override
            def get_oci_container(self, spec):
                raise NotImplementedError

            @override
            def report_progress(self):
                raise NotImplementedError

            @override
            def cache_check(self, key: bytes) -> bool:
                return cache.has(key)

            @override
            def cache_load_path(self, key: bytes) -> Path:
                # print("cache hit!")
                return cache.get_path(key)

            @override
            def cache_store_path(self, key: bytes, path: Path) -> Path:
                return cache.store_path(key, path)

            @override
            def get_global_state[T: GlobalState](self, state_class: type[T]) -> T:
                if state_class not in global_state:
                    global_state[state_class] = state_class(self)

                return global_state[state_class]

            @override
            def get_param(self, key: str) -> Any:
                raise NotImplementedError()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                pass

        class BasicEvaluationContext(BaseEvaluationContext):
            @override
            async def execute_operation(self, operation: Operation) -> Any:
                with BasicOperationContext() as op_ctx:
                    # print(f"Running op {operation}")
                    return await operation.execute(op_ctx)

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
        }

        evaluation_context = BasicEvaluationContext(args.file, buildins=buildins)

        result = evaluate_context(evaluation_context)

        # exit(1)
        if not args.target:
            print("No target specified, available targets:")
            for target in result.attrs():
                print(f"  {target}")

        elif not result.has_attr(args.target):
            print(f"No target '{args.target}' in {args.file}")
        else:
            obj = await result.get_attr(args.target)
            print(obj.path)
        pass

        for state_obj in global_state.values():
            state_obj.done()

    asyncio.run(main())
