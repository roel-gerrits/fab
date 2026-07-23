from pathlib import Path
from typing import override
from fab.model import Cache


class CacheHitCounter(Cache):
    def __init__(self, base: Cache) -> None:
        self.__base = base
        self.__nr_hits = 0
        self.__nr_misses = 0

    @override
    def has(self, op_key: bytes) -> bool:
        result = self.__base.has(op_key)
        if result:
            self.__nr_hits += 1
        else:
            self.__nr_misses += 1
        return result

    @override
    def get_path(self, op_key: bytes) -> Path:
        return self.__base.get_path(op_key)

    @override
    def store_path(self, op_key: bytes, path: Path) -> Path:
        return self.__base.store_path(op_key, path)

    @property
    def hits(self):
        return self.__nr_hits

    @property
    def misses(self):
        return self.__nr_misses
