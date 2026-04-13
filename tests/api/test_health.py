"""Tests for health endpoints."""

import pytest
from httpx import AsyncClient

from openfactcheck import __version__

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_root(client: AsyncClient) -> None:
    """GET / returns service identity with name, version, and status."""
    response = await client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "OpenFactCheck API"
    assert body["version"] == __version__
    assert body["status"] == "running"


async def test_health(client: AsyncClient) -> None:
    """GET /health returns healthy status."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
