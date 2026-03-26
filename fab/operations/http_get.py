
import aiohttp
import yarl

from ..building import Context, create_key
from ..data.base import PathObj, String
from .decorator import operation


@operation
async def http_get(
    context: Context, url: String, sha256: String | None = None
) -> PathObj:
    parsed_url = yarl.URL(url.value)

    key = create_key(context, [sha256 or url])

    if context.cache.has(key):
        return PathObj(context.cache.get_path(key))

    sandbox = context.sandbox_factory.create()
    filename = sandbox / parsed_url.name
    with open(filename, "wb") as f:
        async with aiohttp.ClientSession() as session:
            async with session.get(parsed_url) as resp:
                resp.raise_for_status()
                async for chunk in resp.content.iter_chunked(1024 * 32):
                    f.write(chunk)
                    # print(".", end="", flush=True)

    cached_path = context.cache.store_path(key, filename)
    return PathObj(cached_path)
