from hashlib import sha256
from pathlib import Path
from typing import override

import aiohttp
import yarl

from ..model import Operation, OperationContext
from ..util.hash_objects import hash_objects


class HttpGet(Operation):
    def __init__(self, url: str) -> None:
        self.__url = url

    @override
    async def execute(self, context: OperationContext) -> Path:
        parsed_url = yarl.URL(self.__url)

        key = hash_objects(sha256(), self.__url)

        if context.cache_check(key):
            return context.cache_load_path(key)

        sandbox = context.get_sandbox()
        download_result = sandbox / parsed_url.name
        with open(download_result, "wb") as f:
            async with aiohttp.ClientSession() as session:
                async with session.get(parsed_url) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.content.iter_chunked(1024 * 32):
                        f.write(chunk)
                        # print(".", end="", flush=True)

        cached_path = context.cache_store_path(key, download_result)

        return cached_path
