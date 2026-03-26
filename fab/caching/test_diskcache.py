import hashlib
from pathlib import Path

from ..util.hash_path import hash_path
from ..util.temp_file_structure import TempFileStructure
from .abc import Key
from .diskcache import DiskCache


def path_key(path: Path) -> str:
    hashfunc = hashlib.sha256()
    return hash_path(hashfunc, path).hex()


def test_store_has_get_path():
    with TempFileStructure(
        [
            ("objects/file1", "file1"),
            ("cache_dir/", None),
        ]
    ) as root:
        cache = DiskCache(root / "cache_dir")
        file = root / "objects/file1"
        op_key = Key.from_hex("abcdef1234567890")
        original_key = path_key(file)

        assert not cache.has(op_key)
        cached_file = cache.store_path(op_key, file)

        assert path_key(cached_file) == original_key
        assert cache.has(op_key)

        retrieved_file = cache.get_path(op_key)
        assert path_key(retrieved_file) == original_key


def test_store_again():
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
        op1_key = Key.from_hex("abcd01")
        op2_key = Key.from_hex("abcd02")
        cached_file1 = cache.store_path(op1_key, file1)
        cached_file2 = cache.store_path(op2_key, file2)

        assert path_key(cached_file1) == path_key(cached_file2)
