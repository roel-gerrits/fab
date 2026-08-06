from pathlib import Path
from typing import override
from ..model import Cache
from datetime import datetime


class CacheLogger(Cache):
    def __init__(self, logfile: Path, base: Cache) -> None:
        self.__base = base
        logfile.parent.mkdir(parents=True, exist_ok=True)
        self.__logfile = open(logfile, "a")

    def __log_hit(self, key: bytes):
        time_str = datetime.now().isoformat()
        self.__logfile.write(f"{time_str} {key.hex()}\n")

    def __del__(self):
        self.__logfile.flush()

    @override
    async def has(self, op_key: bytes) -> bool:
        result = await self.__base.has(op_key)
        if result:
            self.__log_hit(op_key)
        return result

    @override
    async def get_path(self, op_key: bytes) -> Path:
        return await self.__base.get_path(op_key)

    @override
    async def store_path(self, op_key: bytes, path: Path) -> Path:
        return await self.__base.store_path(op_key, path)
