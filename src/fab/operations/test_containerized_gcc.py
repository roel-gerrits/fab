from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, override

import pytest

from ..model import OciContainer, OciProcess, OperationContext, OutputChunk, StreamType
from .containerized_gcc import GccLink, _parse_make_deps


def test_parse_make_deps():
    assert list(_parse_make_deps(
        "main.o: main.cpp lib1.h lib2.h \\\n lib3.h lib4.h \\\n lib5.h path\\ with\\ spaces.h"
    )) == [
        Path("lib1.h"),
        Path("lib2.h"),
        Path("lib3.h"),
        Path("lib4.h"),
        Path("lib5.h"),
        Path("path with spaces.h"),
    ]



async def _empty_chunks() -> AsyncIterator[OutputChunk]:
    for _ in ():
        yield OutputChunk(StreamType.STDOUT, b"")


class FakeProcess(OciProcess):
    @override
    async def wait(self) -> int:
        return 0


class FakeContainer(OciContainer):
    def __init__(self) -> None:
        self.cmd: list[str] = []
        self.working_dir: str = ""

    @override
    async def start(self):
        raise NotImplementedError

    @override
    async def stop(self):
        raise NotImplementedError

    @override
    async def kill(self):
        raise NotImplementedError

    @override
    async def remove(self):
        raise NotImplementedError

    @override
    async def exec(
        self,
        cmd: list[str],
        working_dir: str,
        user: str | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[OciProcess, AsyncIterator[OutputChunk]]:
        self.cmd = cmd
        self.working_dir = working_dir
        return FakeProcess(), _empty_chunks()


class RecordingContext(OperationContext):
    def __init__(self, root: Path) -> None:
        self.__root = root
        self.image: str | None = None
        self.container: FakeContainer | None = None
        self.keys: list[bytes] = []

    @override
    def get_sandbox(self) -> Path:
        return self.__root

    @override
    async def get_oci_container(
        self,
        image: str,
        working_dir: str | None = None,
        cmd: list[str] | None = None,
        user: str | None = None,
        host_mountpoint: Path | None = None,
    ) -> OciContainer:
        self.image = image
        self.container = FakeContainer()
        return self.container

    @override
    def report_progress(self) -> None:
        raise NotImplementedError

    @override
    async def cache_check(self, key: bytes) -> bool:
        self.keys.append(key)
        return False

    @override
    async def cache_load_path(self, key: bytes) -> Path:
        raise NotImplementedError

    @override
    async def cache_store_path(self, key: bytes, path: Path) -> Path:
        return path

    @override
    def get_param(self, key: str) -> Any:
        raise NotImplementedError

    @override
    def get_global_state[T](self, state_class: type[T]) -> T:
        raise NotImplementedError

    @override
    def cleanup(self) -> None:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_link_options_appended(tmp_path: Path):
    context = RecordingContext(tmp_path)
    obj = tmp_path / "obj.o"
    obj.write_bytes(b"content")
    op = GccLink(
        "img", None, "out", [obj], options=["-lm", "-Wl,--as-needed"]
    )
    await op.execute(context)
    assert context.container is not None
    cmd = context.container.cmd
    assert cmd[0:3] == ["g++", "-o", "out"]
    assert cmd[-2:] == ["-lm", "-Wl,--as-needed"]


@pytest.mark.asyncio
async def test_link_options_in_cache_key(tmp_path: Path):
    obj = tmp_path / "obj.o"
    obj.write_bytes(b"content")

    ctx1 = RecordingContext(tmp_path)
    op1 = GccLink("img", None, "out", [obj], options=["-lm"])
    await op1.execute(ctx1)

    ctx2 = RecordingContext(tmp_path)
    op2 = GccLink("img", None, "out", [obj], options=["-ldl"])
    await op2.execute(ctx2)

    assert len(ctx1.keys) == len(ctx2.keys) == 1
    assert ctx1.keys[0] != ctx2.keys[0]


@pytest.mark.asyncio
async def test_link_without_options(tmp_path: Path):
    context = RecordingContext(tmp_path)
    obj = tmp_path / "obj.o"
    obj.write_bytes(b"content")
    op = GccLink("img", None, "out", [obj])
    await op.execute(context)
    assert context.container is not None
    assert context.container.cmd == ["g++", "-o", "out", "/host_root" + str(obj)]
