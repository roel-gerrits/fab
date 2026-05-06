from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class GlobalState(ABC):
    @abstractmethod
    def __init__(self, context: OperationContext) -> None:
        pass

    def done(self):
        pass


class OperationContext(ABC):
    @abstractmethod
    def get_sandbox(self) -> Path: ...

    @abstractmethod
    def get_oci_container(self, spec): ...

    @abstractmethod
    def report_progress(self): ...

    @abstractmethod
    def cache_check(self, key: bytes) -> bool: ...

    @abstractmethod
    def cache_load_path(self, key: bytes) -> Path: ...

    @abstractmethod
    def cache_store_path(self, key: bytes, path: Path) -> Path: ...

    @abstractmethod
    def get_param(self, key: str) -> Any: ...

    @abstractmethod
    def get_global_state[T: GlobalState](self, state_class: type[T]) -> T: ...


class Operation(ABC):
    async def execute(self, context: OperationContext) -> Any: ...
