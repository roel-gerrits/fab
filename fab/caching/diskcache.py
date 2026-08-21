from typing import override
from pathlib import Path

from .cache_logger import CacheLogger
from ..model import Cache

from ..util.string_slices import string_slices
from ..util.hash_path import hash_path

import blake3


class DiskCacheError(RuntimeError):
    pass


class Log:
    def __init__(self, path: Path) -> None:
        self.__path = path
        self.__path.parent.mkdir(parents=True, exist_ok=True)
        self.__writer = open(self.__path, "a")

    def __del__(self):
        self.flush()

    def write(self, timestamp: datetime, key: bytes):
        time_str = timestamp.isoformat()
        self.__writer.write(f"{time_str} {key.hex()}\n")

    def flush(self):
        self.__writer.flush()

    def read_entries(self) -> Generator[tuple[datetime, bytes]]:
        """Read entries from log, most recent first."""

        self.flush()

        # NOTE: This approach is very inefficient for large files, will need refactoring at some point!
        for line in reversed(self.__path.read_text().splitlines()):
            parts = line.split(" ", 1)
            timestamp = datetime.fromisoformat(parts[0])
            key = bytes.fromhex(parts[1])
            yield timestamp, key

class ActualDiskCache(Cache):
    def __init__(self, root: Path) -> None:

        self.__ops = root / "v1/ops"
        self.__ops.mkdir(parents=True, exist_ok=True)

        self.__blobs = root / "v1/blobs"
        self.__blobs.mkdir(parents=True, exist_ok=True)

    def __get_op_path(self, op_key: bytes) -> Path:
        key_parts = string_slices(op_key.hex(), 2, 2)
        return self.__ops / key_parts[0] / key_parts[1] / op_key.hex()

    def __get_blob_path(self, blob_key: bytes) -> Path:
        key_parts = string_slices(blob_key.hex(), 2, 2)
        return self.__blobs / key_parts[0] / key_parts[1] / blob_key.hex()

    @override
    async def has(self, op_key: bytes) -> bool:
        op_path = self.__get_op_path(op_key)
        return op_path.exists()

    @override
    async def get_path(self, op_key: bytes) -> Path:
        op_path = self.__get_op_path(op_key)
        if not op_path.is_dir():
            raise DiskCacheError(f"{op_path} does not exist")

        object_link = op_path / "object"
        if not object_link.is_symlink():
            raise DiskCacheError(f"Corrupt cache, {object_link} is not a symlink")

        blob_path = object_link.resolve()

        return blob_path

    @override
    async def store_path(self, op_key: bytes, path: Path) -> Path:
        if not path.exists():
            raise DiskCacheError(f"Cannot store non-existent path {path} in cache")

        blob_key = hash_path(blake3.blake3(), path)

        blob_path = self.__get_blob_path(blob_key)
        blob_path.mkdir(parents=True, exist_ok=True)
        obj_path = blob_path / path.name
        if not obj_path.exists():
            path.rename(obj_path)

        op_path = self.__get_op_path(op_key)
        if op_path.exists():
            raise DiskCacheError(
                f"Operation with key '{op_key.hex()}' already exists in cache"
            )

        op_path.mkdir(parents=True, exist_ok=True)
        (op_path / "object").symlink_to(obj_path.relative_to(op_path, walk_up=True))

        return obj_path
