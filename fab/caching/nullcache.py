from pathlib import Path
from typing import override
from .abc import Cache, Key
from ..data.base import Object


class NullCache(Cache):
    @override
    def has(self, op_key: Key) -> bool:
        return False

    @override
    def get_path(self, op_key: Key) -> Path:
        raise KeyError()

    @override
    def store_path(self, op_key: Key, path: Path) -> Path:
        raise NotImplementedError()
