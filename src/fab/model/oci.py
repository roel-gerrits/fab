from __future__ import annotations
import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass
from .outputchunks import OutputChunk


class OciError(RuntimeError):
    """Raised when an OCI API operation fails."""


class ImageNotFoundError(OciError):
    """Raised when a container image cannot be found."""


class PullError(OciError):
    """Raised when pulling a container image fails."""


@dataclass
class ProgressDetail:
    current: int
    total: int


@dataclass
class PullEvent:
    status: str
    id: str | None = None
    progress_detail: ProgressDetail | None = None


class OciClient(abc.ABC):
    @abc.abstractmethod
    async def create_container(
        self,
        image: str,
        cmd: list[str] | None = None,
        working_dir: str | None = None,
        user: str | None = None,
        bind_mounts: list[tuple[str, str]] | None = None,
        labels: list[tuple[str, str]] | None = None,
        name: str | None = None,
        env: dict[str, str] | None = None,
    ) -> OciContainer: ...

    @abc.abstractmethod
    async def find_container(
        self,
        label: tuple[str, str] | None = None,
        name: str | None = None,
    ) -> OciContainer | None: ...

    @abc.abstractmethod
    async def list_containers(
        self,
        label: tuple[str, str],
    ) -> list[OciContainer]: ...

    @abc.abstractmethod
    async def pull_image(self, image: str) -> AsyncIterator[PullEvent]: ...


class OciContainer(abc.ABC):
    @abc.abstractmethod
    async def start(self): ...

    @abc.abstractmethod
    async def stop(self): ...

    @abc.abstractmethod
    async def kill(self): ...

    @abc.abstractmethod
    async def remove(self): ...

    @abc.abstractmethod
    async def exec(
        self,
        cmd: list[str],
        working_dir: str,
        user: str | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[OciProcess, AsyncIterator[OutputChunk]]: ...


class OciProcess(abc.ABC):
    @abc.abstractmethod
    async def wait(self) -> int: ...
