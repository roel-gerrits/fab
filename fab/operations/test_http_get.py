import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import override

import aiohttp
import aiohttp.test_utils
import aiohttp.web
import pytest

from ..caching import DiskCache
from ..model import OperationContext
from .http_get import HttpGet


class DummyOperationContext(OperationContext):
    def __init__(self, root: Path) -> None:
        self.__root = root
        self.__cache = DiskCache(self.__root / "cache")

    @override
    def get_sandbox(self) -> Path:
        return self.__root / tempfile.mkdtemp(dir=self.__root)

    @override
    def get_oci_container(self, spec):
        raise NotImplementedError

    @override
    def report_progress(self):
        pass

    @override
    def cache_check(self, key: bytes) -> bool:
        return self.__cache.has(key)

    @override
    def cache_load_path(self, key: bytes) -> Path:
        return self.__cache.get_path(key)

    @override
    def cache_store_path(self, key: bytes, path: Path) -> Path:
        return self.__cache.store_path(key, path)


class FileServer:
    def __init__(self, files: Sequence[tuple[str, str]]):
        self.files = files

        def serve_text(text: str):
            async def serve(request):
                return aiohttp.web.Response(text=text)

            return serve

        app = aiohttp.web.Application()
        for path, content in files:
            app.router.add_get(path, serve_text(content))
        self.__server = aiohttp.test_utils.TestServer(app)

    async def __aenter__(self):
        await self.__server.start_server()
        return self

    async def __aexit__(self, *_):
        await self.__server.close()

    def make_url(self, path: str) -> str:
        return str(self.__server.make_url(path))


@pytest.mark.asyncio
async def test_simple(tmp_path: Path):
    async with FileServer(
        [
            ("/file1.txt", "file1_content"),
        ]
    ) as server:
        op = HttpGet(server.make_url("file1.txt"))
        ctx = DummyOperationContext(tmp_path)
        result = await op.execute(ctx)

        assert isinstance(result, Path)
        assert result.read_text() == "file1_content"
        assert result.name == "file1.txt"


@pytest.mark.asyncio
async def test_cache(tmp_path: Path):

    async with FileServer(
        [
            ("/some_file.txt", "some_file_content"),
        ]
    ) as server:
        op = HttpGet(server.make_url("some_file.txt"))
        ctx = DummyOperationContext(tmp_path)
        result1 = await op.execute(ctx)
        result2 = await op.execute(ctx)

        assert isinstance(result1, Path)
        assert isinstance(result2, Path)
        assert result1 == result2
        print(result1)
