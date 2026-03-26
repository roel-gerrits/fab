import argparse
import asyncio
import hashlib
from pathlib import Path

from fab.caching import DiskCache, MemoryCache
from fab.lang.interpreter import (
    Evaluator,
    LoadFileFunc,
    LocalFileLookup,
    evaluate_source,
)
from . import operations
from .building import Context
from .building.sandboxes import SandboxFactory

parser = argparse.ArgumentParser()
parser.add_argument("target", nargs="?", type=str)
parser.add_argument("-f", "--file", default="build.txt", type=Path)



async def main():
    args = parser.parse_args()

    file_lookup = LocalFileLookup(Path.cwd())
    source = file_lookup.lookup(args.file)

    # cache = MemoryCache()
    cache = DiskCache(Path(".fab/cache"))
    sandbox_factory = SandboxFactory(Path(".fab/sandboxes"))
    context = Context(cache, hashlib.sha256, None, sandbox_factory)
    evaluator = Evaluator(context)
    evaluator.add_symbol("load", LoadFileFunc(file_lookup, evaluator))
    evaluator.add_symbol("http_get", operations.http_get)
    evaluator.add_symbol("extract", operations.extract)
    evaluator.add_symbol("http_archive", operations.http_archive)
    evaluator.add_symbol("compile", operations.gcc_compile)
    evaluator.add_symbol("link", operations.gcc_link)
    evaluator.add_symbol("path", operations.local_path)
    result = evaluate_source(evaluator, source)

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


asyncio.run(main())
