from __future__ import annotations
from collections.abc import Iterable, Sequence
from pathlib import Path

from .hash_path import chunkify_path

Hashable = str | bytes | Path | None | Sequence["Hashable"]


def chunkify_objects(*objs: Hashable) -> Iterable[bytes]:
    for obj in objs:
        if obj is None:
            yield b"NONE"
        elif isinstance(obj, str):
            yield b"STR"
            yield obj.encode()
        elif isinstance(obj, bytes):
            yield b"BYTES"
            yield obj
        elif isinstance(obj, Path):
            yield b"PATH"
            yield from chunkify_path(obj)
        elif isinstance(obj, Sequence):
            yield b"SEQ"
            for item in obj:
                yield from chunkify_objects(item)
        else:
            raise TypeError(f"Unsupported type {type(obj).__name__}")


def hash_objects(hash_func, *obj: Hashable) -> bytes:
    for chunk in chunkify_objects(obj):
        hash_func.update(chunk)
    return hash_func.digest()
