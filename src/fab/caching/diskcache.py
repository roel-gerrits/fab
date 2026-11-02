from __future__ import annotations

import dataclasses
import os
import shutil
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import override

import blake3

from ..model import Cache
from ..util.hash_path import hash_path
from ..util.string_slices import string_slices


class DiskCacheError(RuntimeError):
    pass


class Log:
    MAX_KEY_LENGTH = 32  # bytes
    RECORD_LENGTH = len("YYYY-MM-DDTHH:MM:SS " + (MAX_KEY_LENGTH) * "00" + "\n")

    def __init__(self, path: Path):
        self.__path = path
        self.__fd = self.__open(self.__path)

    def __open(self, path: Path) -> int:
        fd = os.open(path, os.O_APPEND | os.O_RDWR | os.O_CREAT)
        os.lseek(fd, 0, os.SEEK_END)
        return fd

    def write(self, timestamp: datetime, op_key: bytes):
        assert len(op_key) <= self.MAX_KEY_LENGTH
        time_str = timestamp.isoformat(timespec="seconds")
        os.write(
            self.__fd,
            f"{time_str} {op_key.hex().ljust(self.MAX_KEY_LENGTH * 2)}\n".encode(),
        )

    def read_new_to_old(self) -> Generator[tuple[datetime, bytes]]:
        position = os.lseek(self.__fd, 0, os.SEEK_CUR) - self.RECORD_LENGTH
        while position >= 0:
            record = self.__read_record(position)
            if record is None:
                break
            yield record
            position -= self.RECORD_LENGTH

    def oldest_entry(self) -> tuple[datetime, bytes] | None:
        """Return the oldest entry from the log"""
        return self.__read_record(0)

    def newest_entry(self) -> tuple[datetime, bytes] | None:
        """Return the newest entry from the log"""
        position = os.lseek(self.__fd, 0, os.SEEK_CUR) - self.RECORD_LENGTH
        if position < 0:
            return None
        return self.__read_record(position)

    def record_count(self) -> int:
        end = os.lseek(self.__fd, 0, os.SEEK_CUR)
        return end // self.RECORD_LENGTH

    def replace_with(self, other: Log):
        os.close(self.__fd)
        os.rename(other.__path, self.__path)
        self.__fd = self.__open(self.__path)

    def __read_record(self, position) -> tuple[datetime, bytes] | None:
        record = os.pread(self.__fd, self.RECORD_LENGTH, position).decode()
        if len(record) != self.RECORD_LENGTH:
            return None
        time_str, _, key_str = record.partition(" ")
        timestamp = datetime.fromisoformat(time_str)
        op_key = bytes.fromhex(key_str)
        return timestamp, op_key


@dataclasses.dataclass
class DiskCacheInfo:
    path: Path
    n_ops: int
    n_blobs: int
    size_blobs: int
    oldest_op: datetime | None
    newest_op: datetime | None
    log_records: int


class DiskCache(Cache):
    def __init__(self, root: Path) -> None:
        self.__root = root
        self.__ops = root / "v1/ops"
        self.__ops.mkdir(parents=True, exist_ok=True)

        self.__blobs = root / "v1/blobs"
        self.__blobs.mkdir(parents=True, exist_ok=True)

        self.__log_path = root / "v1/log"
        self.__log = Log(self.__log_path)

    @override
    async def has(self, op_key: bytes) -> bool:
        op_path = self.__get_op_path(op_key)
        result = op_path.exists()
        if result:
            self.__log.write(datetime.now(), op_key)
        return result

    @override
    async def get_path(self, op_key: bytes) -> Path:
        return self.__get_path(op_key)

    def __get_path(self, op_key: bytes) -> Path:
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

        self.__log.write(datetime.now(), op_key)
        return obj_path

    def prune_to_size(self, size: int):

        kept_ops: dict[bytes, datetime] = dict()
        kept_blobs: set[bytes] = set()
        kept_blobs_size: int = 0
        discarded_ops: set[bytes] = set()
        discarded_blobs: set[bytes] = set()

        for timestamp, op_key in self.__log.read_new_to_old():
            blob_path = self.__get_path(op_key)
            blob_size = blob_path.stat().st_size
            blob_key = bytes.fromhex(blob_path.parent.name)

            if blob_key not in kept_blobs and kept_blobs_size + blob_size <= size:
                kept_blobs.add(blob_key)
                kept_blobs_size += blob_size

            if blob_key in kept_blobs:
                if op_key not in kept_ops:
                    kept_ops[op_key] = timestamp
            else:
                discarded_ops.add(op_key)
                discarded_blobs.add(blob_key)

        for op_key in discarded_ops:
            self.__discard_op(op_key)

        for blob_key in discarded_blobs:
            self.__discard_blob(blob_key)

        new_log = Log(self.__log_path.with_suffix(".new"))
        for op_key, timestamp in reversed(kept_ops.items()):
            new_log.write(timestamp, op_key)

        self.__log.replace_with(new_log)

    def prune_to_age(self, timestamp: datetime):
        """Remove all entries that have not been used after timestamp."""
        # TODO, sometime...
        raise NotImplementedError()

    def get_info(self) -> DiskCacheInfo:

        n_ops = 0
        blob_keys: set[bytes] = set()
        size_blobs = 0

        for op_path in self.__scan_ops():
            n_ops += 1
            object_path = op_path / "object"
            blob_key = bytes.fromhex(object_path.parent.name)

            if blob_key in blob_keys:
                continue

            blob_keys.add(blob_key)
            blob_path = object_path.resolve()
            size_blobs += blob_path.stat().st_size

        oldest_op = self.__log.oldest_entry()
        newest_op = self.__log.newest_entry()

        return DiskCacheInfo(
            path=self.__root,
            n_ops=n_ops,
            n_blobs=len(blob_keys),
            size_blobs=size_blobs,
            oldest_op=oldest_op[0] if oldest_op else None,
            newest_op=newest_op[0] if newest_op else None,
            log_records=self.__log.record_count(),
        )

    def __get_op_path(self, op_key: bytes) -> Path:
        key_parts = string_slices(op_key.hex(), 2, 2)
        return self.__ops / key_parts[0] / key_parts[1] / op_key.hex()

    def __get_blob_path(self, blob_key: bytes) -> Path:
        key_parts = string_slices(blob_key.hex(), 2, 2)
        return self.__blobs / key_parts[0] / key_parts[1] / blob_key.hex()

    def __discard_op(self, op_key: bytes):
        op_path = self.__get_op_path(op_key)
        os.unlink(op_path / "object")
        os.rmdir(op_path)

    def __discard_blob(self, blob_key: bytes):
        blob_path = self.__get_blob_path(blob_key)
        shutil.rmtree(blob_path)

    def __scan_ops(self) -> Generator[Path]:
        for dir1 in os.scandir(self.__ops):
            for dir2 in os.scandir(dir1):
                for entry in os.scandir(dir2):
                    yield Path(entry.path)
