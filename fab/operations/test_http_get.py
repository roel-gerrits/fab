import hashlib
from collections.abc import Sequence
from pathlib import Path
import tempfile

import aiohttp
import aiohttp.test_utils
import aiohttp.web
import pytest
import pytest_asyncio

from fab.building.sandboxes import SandboxFactory
from fab.caching.diskcache import DiskCache


from ..building import Context
from ..caching import Cache, DiskCache, NullCache
from ..data.base import PathObj, String
from .http_get import http_get


class DummyContext(Context):
    def __init__(
        self,
        cache: Cache = NullCache(),
        hash_algo=hashlib.md5,
        http_session=None,
        sandbox_factory=SandboxFactory(Path(tempfile.mkdtemp())),
    ):
        super().__init__(cache, hash_algo, http_session, sandbox_factory)


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


@pytest.fixture
def disk_cache():
    with tempfile.TemporaryDirectory() as dir:
        cache = DiskCache(Path(dir))
        yield cache


@pytest.mark.asyncio
async def test_simple(disk_cache: DiskCache):

    async with FileServer(
        [
            ("/file1.txt", "file1_content"),
        ]
    ) as server:
        result = await http_get.execute(
            DummyContext(cache=disk_cache),
            args=[String(str(server.make_url("file1.txt")))],
            kwargs={},
        )

        assert isinstance(result, PathObj)
        assert result.path.read_text() == "file1_content"
        assert result.path.name == "file1.txt"


@pytest.mark.asyncio
async def test_cache(disk_cache: DiskCache):

    async with FileServer(
        [
            ("/some_file.txt", "some_file_content"),
        ]
    ) as server:
        url = String(str(server.make_url("some_file.txt")))

        result1 = await http_get.execute(
            DummyContext(cache=disk_cache),
            args=[url],
            kwargs={},
        )

        result2 = await http_get.execute(
            DummyContext(cache=disk_cache),
            args=[url],
            kwargs={},
        )

        assert isinstance(result1, PathObj)
        assert isinstance(result2, PathObj)
        assert result1.path == result2.path
