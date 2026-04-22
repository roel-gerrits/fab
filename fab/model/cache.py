from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path


class Cache(ABC):
    @abstractmethod
    def has(self, op_key: bytes) -> bool: ...

    @abstractmethod
    def get_path(self, op_key: bytes) -> Path: ...

    @abstractmethod
    def store_path(self, op_key: bytes, path: Path) -> Path: ...
