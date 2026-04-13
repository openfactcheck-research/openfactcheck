"""Tests for error handling middleware."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_app_error_returns_json(client: AsyncClient) -> None:
    """AppError (404) returns structured JSON with detail, code, and status."""
    response = await client.get("/api/v1/projects/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["status"] == 404
    assert "detail" in body


async def test_validation_error_returns_422(client: AsyncClient) -> None:
    """FastAPI validation errors return 422 for invalid request bodies."""
    response = await client.post("/api/v1/projects/", json={})

    assert response.status_code == 422
