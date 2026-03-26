from pathlib import Path
from ..building import Context, create_key
from ..data.base import PathObj, String
from .decorator import operation

import shutil

@operation
async def extract(context: Context, archive: PathObj) -> PathObj:

    key = create_key(context, [b"unpack", archive])

    if context.cache.has(key):
        return PathObj(context.cache.get_path(key))

    sandbox = context.sandbox_factory.create()
    extract_dir = sandbox / archive.path.name
    extract_dir.mkdir()

    shutil.unpack_archive(archive.path, extract_dir)

    cached_path = context.cache.store_path(key, extract_dir)
    return PathObj(cached_path)
