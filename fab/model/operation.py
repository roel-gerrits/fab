from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fab.model.oci import OciContainer


class OperationContext(ABC):
    @abstractmethod
    def get_sandbox(self) -> Path: ...

    @abstractmethod
    async def get_oci_container(
        self,
        image: str,
        working_dir: str | None = None,
        cmd: list[str] | None = None,
        user: str | None = None,
        host_mountpoint: Path | None = None,
    ) -> OciContainer: ...

    @abstractmethod
    def report_progress(self): ...

    @abstractmethod
    async def cache_check(self, key: bytes) -> bool: ...

    @abstractmethod
    async def cache_load_path(self, key: bytes) -> Path: ...

    @abstractmethod
    async def cache_store_path(self, key: bytes, path: Path) -> Path: ...

    @abstractmethod
    def get_param(self, key: str) -> Any: ...

    @abstractmethod
    def get_global_state[T](self, state_class: type[T]) -> T: ...

    @abstractmethod
    def cleanup(self): ...


class Operation(ABC):
    @abstractmethod
    async def execute(self, context: OperationContext) -> Any: ...


class OperationError(RuntimeError):
    error_line: str
    error_msg: str

    def __init__(self, error_line: str, error_msg: str) -> None:
        self.error_line = error_line
        self.error_msg = error_msg
        super().__init__(error_line)
