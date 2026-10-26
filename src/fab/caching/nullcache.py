from pathlib import Path
from typing import override
from ..model import Cache

class NullCache(Cache):
    @override
    async def has(self, op_key: bytes) -> bool:
        return False

    @override
    async def get_path(self, op_key: bytes) -> Path:
        raise KeyError()

    @override
    async def store_path(self, op_key: bytes, path: Path) -> Path:
        raise NotImplementedError()
