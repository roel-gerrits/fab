import shutil
import string
from typing import override
from .abc import Cache, Key
from pathlib import Path

from ..util.string_slices import string_slices
from ..util.hash_path import hash_path

import blake3


class DiskCacheError(RuntimeError):
    pass


class DiskCache(Cache):
    def __init__(self, root: Path) -> None:

        self.__ops = root / "v1/ops"
        self.__ops.mkdir(parents=True, exist_ok=True)

        self.__blobs = root / "v1/blobs"
        self.__blobs.mkdir(parents=True, exist_ok=True)

    def __get_op_path(self, op_key: Key) -> Path:
        key_parts = string_slices(op_key.as_hex(), 2, 2)
        return self.__ops / key_parts[0] / key_parts[1] / op_key.as_hex()

    def __get_blob_path(self, blob_key: bytes) -> Path:
        key_parts = string_slices(blob_key.hex(), 2, 2)
        return self.__blobs / key_parts[0] / key_parts[1] / blob_key.hex()

    @override
    def has(self, op_key: Key) -> bool:
        op_path = self.__get_op_path(op_key)
        return op_path.exists()

    @override
    def get_path(self, op_key: Key) -> Path:
        op_path = self.__get_op_path(op_key)
        if not op_path.is_dir():
            raise DiskCacheError(f"{op_path} does not exist")

        object_link = op_path / "object"
        if not object_link.is_symlink():
            raise DiskCacheError(f"Corrupt cache, {object_link} is not a symlink")

        blob_path = object_link.resolve()

        return blob_path

    @override
    def store_path(self, op_key: Key, path: Path) -> Path:
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
                f"Operation with key '{op_key.as_hex()}' already exists in cache"
            )

        op_path.mkdir(parents=True, exist_ok=True)
        (op_path / "object").symlink_to(obj_path.relative_to(op_path, walk_up=True))

        return obj_path
