import random
from pathlib import Path
from typing import override

from ..model import Cache


class AnonCache(Cache):
    def __init__(self, backend: Cache):
        self.__key = random.randbytes(64)
        self.__backend = backend

    def __anonimize_key(self, key: bytes) -> bytes:
        assert len(key) <= len(self.__key)
        return bytes(a ^ b for a, b in zip(key, self.__key))

    @override
    async def has(self, op_key: bytes) -> bool:
        return await self.__backend.has(self.__anonimize_key(op_key))

    @override
    async def get_path(self, op_key: bytes) -> Path:
        return await self.__backend.get_path(self.__anonimize_key(op_key))

    @override
    async def store_path(self, op_key: bytes, path: Path) -> Path:
        return await self.__backend.store_path(self.__anonimize_key(op_key), path)
