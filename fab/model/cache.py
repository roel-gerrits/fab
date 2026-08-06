from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path


class Cache(ABC):
    @abstractmethod
    async def has(self, op_key: bytes) -> bool: ...

    @abstractmethod
    async def get_path(self, op_key: bytes) -> Path: ...

    @abstractmethod
    async def store_path(self, op_key: bytes, path: Path) -> Path: ...
