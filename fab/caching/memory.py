from pathlib import Path
from typing import override

from ..data.base import Object
from .abc import Cache, Key


class MemoryCache(Cache):
    def __init__(self):
        self.__cached_paths: dict[Key, Path] = {}

    @override
    def has(self, op_key: Key) -> bool:
        return op_key in self.__cached_paths

    @override
    def get_path(self, op_key: Key) -> Path:
        return self.__cached_paths[op_key]

    @override
    def store_path(self, op_key: Key, path: Path) -> Path:
        self.__cached_paths[op_key] = path
        return path

    def print_cache(self) -> None:
        for key, value in self.__cached_paths.items():
            print(f"{key.as_hex()}: {value}")
