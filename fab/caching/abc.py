from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import override


from ..data.base import Object


class HashFunc(ABC):
    @abstractmethod
    def update(self, data: bytes) -> None: ...

    @abstractmethod
    def digest(self) -> bytes: ...

    @abstractmethod
    def hexdigest(self) -> str: ...


HashAlgo = Callable[[], HashFunc]


class Key:
    value: bytes

    def __init__(self, value: bytes) -> None:
        self.value = value

    def as_hex(self) -> str:
        return self.value.hex()

    @staticmethod
    def from_hex(value: str) -> Key:
        return Key(bytes.fromhex(value))

    @override
    def __repr__(self) -> str:
        return f"<Key {self.as_hex()[0:16]}...>"

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, Key):
            return False
        return self.value == other.value


class Cache(ABC):
    @abstractmethod
    def has(self, op_key: Key) -> bool: ...

    @abstractmethod
    def get_path(self, op_key: Key) -> Path: ...

    @abstractmethod
    def store_path(self, op_key: Key, path: Path) -> Path: ...
