import pytest

from .podman import PodmanClient


@pytest.mark.asyncio
async def test_ping():
    client = PodmanClient()
    await client.ping()
