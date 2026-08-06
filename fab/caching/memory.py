from pathlib import Path
from typing import override


from ..model import Cache

class MemoryCache(Cache):
    def __init__(self):
        self.__cached_paths: dict[bytes, Path] = {}

    @override
    async def has(self, op_key: bytes) -> bool:
        return op_key in self.__cached_paths

    @override
    async def get_path(self, op_key: bytes) -> Path:
        return self.__cached_paths[op_key]

    @override
    async def store_path(self, op_key: bytes, path: Path) -> Path:
        self.__cached_paths[op_key] = path
        return path

    def print_cache(self) -> None:
        for key, value in self.__cached_paths.items():
            print(f"{key.hex()}: {value}")
