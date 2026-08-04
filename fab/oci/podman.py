"""Podman implementation of OciClient / OciContainer / OciProcess.

Uses the Docker-compat REST API exposed by Podman over a Unix socket.

Default socket paths (tried in order):
  1. $DOCKER_HOST              – if set and starts with "unix://"
  2. /run/user/<uid>/podman/podman.sock  – rootless
  3. /run/podman/podman.sock             – rootful / system

The multiplexed exec stream follows the Docker framing protocol:
  [stream_type: 1 byte][0x00 0x00 0x00: 3 bytes][payload_size: 4 bytes BE]
  stream_type: 1 = stdout, 2 = stderr
"""

from __future__ import annotations

import abc
import asyncio
import enum
import json
import os
import struct
from collections.abc import AsyncIterator
from typing import Any, override

import aiohttp

from ..model.oci import (
    ImageNotFoundError,
    OciClient,
    OciContainer,
    OciError,
    OciProcess,
    ProgressDetail,
    PullError,
    PullEvent,
    StreamType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_VERSION = "v1.41"


def _default_socket_path() -> str:
    """Return the best-guess Podman socket path for the current user."""
    docker_host = os.environ.get("DOCKER_HOST", "")
    if docker_host.startswith("unix://"):
        return docker_host[len("unix://") :]

    uid = os.getuid()
    rootless = f"/run/user/{uid}/podman/podman.sock"
    if os.path.exists(rootless):
        return rootless

    return "/run/podman/podman.sock"


async def _raise_for_status(resp: aiohttp.ClientResponse) -> None:
    if resp.status < 400:
        return
    body = await resp.json()
    raise OciError(f"{body.get('cause')}: {body.get('message')}")


# ---------------------------------------------------------------------------
# Multiplexed stream demuxer
# ---------------------------------------------------------------------------


async def _demux_stream(
    resp: aiohttp.ClientResponse,
) -> AsyncIterator[tuple[StreamType, bytes]]:
    """Yield (StreamType, bytes) chunks from a Docker-multiplexed stream.

    Frame format:
        byte 0:   stream type  (1 = stdout, 2 = stderr)
        bytes 1–3: zeros (padding)
        bytes 4–7: payload length (big-endian uint32)
        bytes 8…:  payload
    """
    _TYPE_MAP = {1: StreamType.STDOUT, 2: StreamType.STDERR}
    HEADER = 8

    buf = b""
    async for chunk in resp.content.iter_any():
        buf += chunk
        while len(buf) >= HEADER:
            stream_type_byte, _, _, _, payload_len = struct.unpack_from(
                ">BBBBI", buf, 0
            )
            # Wait until we have the full payload
            if len(buf) < HEADER + payload_len:
                break
            payload = buf[HEADER : HEADER + payload_len]
            buf = buf[HEADER + payload_len :]
            stype = _TYPE_MAP.get(stream_type_byte, StreamType.STDOUT)
            if payload:
                yield stype, payload


# ---------------------------------------------------------------------------
# OciProcess
# ---------------------------------------------------------------------------


class PodmanProcess(OciProcess):
    """Represents a running exec instance inside a Podman container."""

    def __init__(self, session: aiohttp.ClientSession, exec_id: str) -> None:
        self._session = session
        self._exec_id = exec_id

    @override
    async def wait(self) -> int:
        """Poll the exec inspect endpoint until the process exits."""
        while True:
            url = f"http://localhost/{_API_VERSION}/exec/{self._exec_id}/json"
            async with self._session.get(url) as resp:
                await _raise_for_status(resp)
                data = await resp.json()

            running = data.get("Running", False)
            if not running:
                return data["ExitCode"]

            await asyncio.sleep(0.1)


# ---------------------------------------------------------------------------
# OciContainer
# ---------------------------------------------------------------------------


class PodmanContainer(OciContainer):
    """Wraps a single Podman container identified by its ID."""

    def __init__(self, session: aiohttp.ClientSession, container_id: str) -> None:
        self._session = session
        self._id = container_id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        url = f"http://localhost/{_API_VERSION}/containers/{self._id}/start"
        async with self._session.post(url) as resp:
            await _raise_for_status(resp)

    async def stop(self) -> None:
        url = f"http://localhost/{_API_VERSION}/containers/{self._id}/stop"
        async with self._session.post(url) as resp:
            await _raise_for_status(resp)

    async def kill(self) -> None:
        url = f"http://localhost/{_API_VERSION}/containers/{self._id}/kill"
        async with self._session.post(url) as resp:
            await _raise_for_status(resp)

    async def remove(self) -> None:
        url = f"http://localhost/{_API_VERSION}/containers/{self._id}"
        async with self._session.delete(url) as resp:
            await _raise_for_status(resp)

    # ------------------------------------------------------------------
    # Exec
    # ------------------------------------------------------------------

    async def exec(
        self,
        cmd: list[str],
        working_dir: str,
        user: str | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[OciProcess, AsyncIterator[tuple[StreamType, bytes]]]:
        """Create and start an exec instance; return (process, output_stream)."""

        # Step 1: create the exec instance
        create_url = f"http://localhost/{_API_VERSION}/containers/{self._id}/exec"
        create_body = {
            "AttachStdout": True,
            "AttachStderr": True,
            "AttachStdin": False,
            "Tty": False,
            "Cmd": cmd,
            "WorkingDir": working_dir,
        }
        if user is not None:
            create_body["User"] = user
        if env:
            create_body["Env"] = [f"{k}={v}" for k, v in env.items()]

        async with self._session.post(create_url, json=create_body) as resp:
            await _raise_for_status(resp)
            exec_data = await resp.json()

        exec_id = exec_data["Id"]
        process = PodmanProcess(self._session, exec_id)

        # Step 2: start the exec instance and attach to its output stream.
        # We keep the response open and hand back an async generator over it.
        start_url = f"http://localhost/{_API_VERSION}/exec/{exec_id}/start"
        start_body = {"Detach": False, "Tty": False}

        # We cannot use `async with` here because we must keep the response
        # alive for the caller to iterate.  aiohttp allows this pattern when
        # the session outlives the response.
        resp = await self._session.post(
            start_url,
            json=start_body,
            headers={"Content-Type": "application/json"},
        )
        await _raise_for_status(resp)

        stream = _demux_stream(resp)
        return process, stream


# ---------------------------------------------------------------------------
# OciClient
# ---------------------------------------------------------------------------


class PodmanClient(OciClient):
    """OciClient backed by the Podman Docker-compat Unix socket API.

    Usage::

        async with PodmanClient() as client:
            container = await client.create_container(
                image="docker.io/library/alpine:latest",
                cmd=["sleep", "infinity"],
            )
            await container.start()
            process, stream = await container.exec(["echo", "hello"], "/")
            async for stream_type, data in stream:
                print(stream_type, data)
            exit_code = await process.wait()

    The client can also be constructed without the async context manager; call
    :meth:`aclose` explicitly when done.
    """

    def __init__(self, socket_path: str | None = None) -> None:
        resolved = socket_path or _default_socket_path()
        self._session = aiohttp.ClientSession(
            connector=aiohttp.UnixConnector(path=resolved)
        )

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "PodmanClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._session.close()

    # ------------------------------------------------------------------
    # OciClient interface
    # ------------------------------------------------------------------

    async def ping(self) -> None:
        """Check that the Podman service is reachable via the compat API."""
        async with self._session.get("http://localhost/_ping") as resp:
            await _raise_for_status(resp)

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
    ) -> OciContainer:
        """Create (but do not start) a container and return an OciContainer handle."""
        body = {"Image": image}

        if cmd is not None:
            body["Cmd"] = cmd
        if working_dir is not None:
            body["WorkingDir"] = working_dir
        if user is not None:
            body["User"] = user
        if env:
            body["Env"] = [f"{k}={v}" for k, v in env.items()]
        if labels:
            body["Labels"] = dict(labels)

        if bind_mounts:
            # HostConfig.Binds uses "host_path:container_path[:options]" strings
            body["HostConfig"] = {"Binds": [f"{src}:{dst}" for src, dst in bind_mounts]}

        url = f"http://localhost/{_API_VERSION}/containers/create"
        params = {}
        if name is not None:
            params["name"] = name

        async with self._session.post(url, json=body, params=params) as resp:
            if resp.status == 404:
                await resp.read()
                raise ImageNotFoundError(f"Image not found: {image}")
            await _raise_for_status(resp)
            data = await resp.json()

        container_id = data["Id"]
        return PodmanContainer(self._session, container_id)

    async def find_container(
        self,
        label: tuple[str, str] | None = None,
        name: str | None = None,
    ) -> OciContainer | None:
        """Return the first running container matching the given filters, or None."""
        filters = {}
        if label:
            key, value = label
            filters["label"] = [f"{key}={value}"]
        if name:
            filters["name"] = [name]
        url = f"http://localhost/{_API_VERSION}/containers/json"

        async with self._session.get(
            url, params={"filters": json.dumps(filters)}
        ) as resp:
            await _raise_for_status(resp)
            containers = await resp.json()

        if not containers:
            return None

        container_id = containers[0]["Id"]
        return PodmanContainer(self._session, container_id)

    async def list_containers(
        self,
        label: tuple[str, str],
    ) -> list[OciContainer]:
        """Return all containers matching the given label filter."""
        key, value = label
        filters = {"label": [f"{key}={value}"]}
        url = f"http://localhost/{_API_VERSION}/containers/json"
        params = {"filters": json.dumps(filters), "all": "true"}

        async with self._session.get(url, params=params) as resp:
            await _raise_for_status(resp)
            containers = await resp.json()

        return [PodmanContainer(self._session, c["Id"]) for c in containers]

    async def pull_image(self, image: str) -> AsyncIterator[PullEvent]:
        """Pull an image from a registry, yielding progress events."""
        url = f"http://localhost/{_API_VERSION}/images/create"
        params = {"fromImage": image}
        async with self._session.post(url, params=params) as resp:
            if resp.status == 404:
                # await resp.read()
                raise PullError(f"Image not found: {image}")
            await _raise_for_status(resp)
            async for line in resp.content:
                text = line.decode().strip()
                if not text:
                    continue
                data = json.loads(text)
                pd = None
                if data.get("progressDetail"):
                    d = data["progressDetail"]
                    pd = ProgressDetail(current=d["current"], total=d["total"])
                yield PullEvent(
                    status=data.get("status", ""),
                    id=data.get("id"),
                    progress_detail=pd,
                )
