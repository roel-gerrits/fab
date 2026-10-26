import hashlib
from pathlib import Path

import pytest

from ..util.hash_path import hash_path
from ..util.temp_file_structure import TempFileStructure
from .diskcache import DiskCache


def path_key(path: Path) -> str:
    hashfunc = hashlib.sha256()
    return hash_path(hashfunc, path).hex()


@pytest.mark.asyncio
async def test_store_has_get_path():
    with TempFileStructure(
        [
            ("objects/file1", "file1"),
            ("cache_dir/", None),
        ]
    ) as root:
        cache = DiskCache(root / "cache_dir")
        file = root / "objects/file1"
        op_key = bytes.fromhex("abcdef1234567890")
        original_key = path_key(file)

        assert not await cache.has(op_key)
        cached_file = await cache.store_path(op_key, file)

        assert path_key(cached_file) == original_key
        assert await cache.has(op_key)

        retrieved_file = await cache.get_path(op_key)
        assert path_key(retrieved_file) == original_key


@pytest.mark.asyncio
async def test_store_again():
    with TempFileStructure(
        [
            ("objects1/file", "file"),
            ("objects2/file", "file"),
            ("cache_dir/", None),
        ]
    ) as root:
        cache = DiskCache(root / "cache_dir")
        file1 = root / "objects1/file"
        file2 = root / "objects2/file"
        op1_key = bytes.fromhex("abcd01")
        op2_key = bytes.fromhex("abcd02")
        cached_file1 = await cache.store_path(op1_key, file1)
        cached_file2 = await cache.store_path(op2_key, file2)

        assert path_key(cached_file1) == path_key(cached_file2)


def create_file(path: Path, content: str) -> Path:
    with open(path, "w") as f:
        f.write(content)
    return path


@pytest.mark.asyncio
async def test_prune_to_size():
    with TempFileStructure() as root:
        cache = DiskCache(root / "cache_dir")
        op1_key = bytes.fromhex("abcd01")
        op2_key = bytes.fromhex("abcd02")
        file1 = await cache.store_path(op1_key, create_file(root / "file1", "aaa"))
        file2 = await cache.store_path(op2_key, create_file(root / "file2", "bbb"))

        cache.prune_to_size(3)

        assert not await cache.has(op1_key)
        assert not file1.exists()
        assert await cache.has(op2_key)
        assert file2.exists()
