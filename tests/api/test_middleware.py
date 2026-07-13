"""Tests for error handling and external-host middleware."""

import pytest
from httpx import ASGITransport, AsyncClient

from openfactcheck.api.app import create_app
from openfactcheck.api.config import APIConfig

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
    response = await client.post("/api/v1/projects", json={})

    assert response.status_code == 422


async def _redirect_location(external_host: str) -> str:
    app = create_app(APIConfig(auth_bypass=True, debug=True, external_host=external_host))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://internal-host") as client:
        # Routes serve the no-slash path, so a trailing-slash request is the one that redirects.
        response = await client.get("/api/v1/projects/", follow_redirects=False)
    assert response.status_code == 307
    return response.headers["location"]


async def test_external_host_rewrites_redirect_host() -> None:
    """With external_host set, a redirect points at that host, not the request host."""
    assert await _redirect_location("api.example.com") == "http://api.example.com/api/v1/projects"


async def test_no_external_host_keeps_request_host() -> None:
    """Without external_host, a redirect keeps the request's own host."""
    assert await _redirect_location("") == "http://internal-host/api/v1/projects"
