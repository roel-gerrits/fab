from .decorator import operation
from ..data.base import PathObj, List, String
from ..building import Context, create_key
import asyncio


@operation
async def gcc_compile(context: Context, source: PathObj) -> PathObj:

    key = create_key(context, [b"Compile", source])

    if context.cache.has(key):
        return PathObj(context.cache.get_path(key))

    sandbox = context.sandbox_factory.create()

    outputname = source.path.name + ".o"
    cmd = f"gcc -c -o {outputname} {source.path}"
    print(cmd)
    result = await asyncio.create_subprocess_shell(cmd, cwd=sandbox)
    await result.wait()

    cached_path = context.cache.store_path(key, sandbox / outputname)
    return PathObj(cached_path)

@operation
async def gcc_link(context: Context, outputname: String, objects: List) -> PathObj:

    key = create_key(context, [b"Link", objects])

    if context.cache.has(key):
        return PathObj(context.cache.get_path(key))

    sandbox = context.sandbox_factory.create()

    cmd = f"gcc -o {outputname.value} {' '.join([str(entry.path.absolute()) for entry in objects.items])}"
    print(cmd)
    result = await asyncio.create_subprocess_shell(cmd, cwd=sandbox)
    await result.wait()

    cached_path = context.cache.store_path(key, sandbox / outputname.value)
    return PathObj(cached_path)
