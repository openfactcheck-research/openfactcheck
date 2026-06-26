"""Tests for secret management endpoints."""

import pytest
from httpx import AsyncClient

from openfactcheck.api.repositories.constants import MAX_SECRETS_PER_USER

pytestmark = pytest.mark.asyncio(loop_scope="function")

SECRETS_BASE = "/api/v1/secrets"


async def test_set_secret(client: AsyncClient) -> None:
    """PUT stores a secret and returns its masked record."""
    response = await client.put(f"{SECRETS_BASE}/openai", json={"value": "sk-proj-ABCDEFGHwxyz"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "openai"
    assert body["hint"] == "wxyz"


async def test_set_secret_never_returns_value(client: AsyncClient) -> None:
    """The raw value never appears in the set or list responses."""
    value = "sk-proj-ABCDEFGHwxyz"
    set_response = await client.put(f"{SECRETS_BASE}/openai", json={"value": value})
    list_response = await client.get(f"{SECRETS_BASE}/")

    assert value not in set_response.text
    assert value not in list_response.text
    assert "value" not in set_response.json()


async def test_list_secrets(client: AsyncClient) -> None:
    """GET returns the user's secrets ordered by name."""
    await client.put(f"{SECRETS_BASE}/openrouter", json={"value": "value-two-2222"})
    await client.put(f"{SECRETS_BASE}/anthropic", json={"value": "value-one-1111"})

    response = await client.get(f"{SECRETS_BASE}/")

    assert response.status_code == 200
    assert [s["name"] for s in response.json()] == ["anthropic", "openrouter"]


async def test_list_secrets_empty(client: AsyncClient) -> None:
    """GET returns an empty list when no secrets are stored."""
    response = await client.get(f"{SECRETS_BASE}/")

    assert response.status_code == 200
    assert response.json() == []


async def test_set_secret_replaces(client: AsyncClient) -> None:
    """A second PUT replaces the value and updates the hint."""
    await client.put(f"{SECRETS_BASE}/openai", json={"value": "old-value-0000"})
    response = await client.put(f"{SECRETS_BASE}/openai", json={"value": "new-value-9999"})

    assert response.json()["hint"] == "9999"


async def test_set_secret_rejects_invalid_name(client: AsyncClient) -> None:
    """A name that breaks the pattern is rejected."""
    response = await client.put(f"{SECRETS_BASE}/BadName", json={"value": "value-1234"})

    assert response.status_code == 422


async def test_set_secret_rejects_empty_value(client: AsyncClient) -> None:
    """An empty value is rejected."""
    response = await client.put(f"{SECRETS_BASE}/openai", json={"value": ""})

    assert response.status_code == 422


async def test_set_secret_enforces_limit(client: AsyncClient) -> None:
    """Storing a new secret past the limit returns 422."""
    for i in range(MAX_SECRETS_PER_USER):
        assert (await client.put(f"{SECRETS_BASE}/key_{i}", json={"value": "value-1234"})).status_code == 200

    response = await client.put(f"{SECRETS_BASE}/one_too_many", json={"value": "value-1234"})

    assert response.status_code == 422


async def test_delete_secret(client: AsyncClient) -> None:
    """DELETE removes a secret."""
    await client.put(f"{SECRETS_BASE}/openai", json={"value": "value-1234"})

    response = await client.delete(f"{SECRETS_BASE}/openai")

    assert response.status_code == 204
    assert (await client.get(f"{SECRETS_BASE}/")).json() == []


async def test_delete_secret_missing(client: AsyncClient) -> None:
    """Deleting a secret that does not exist returns 404."""
    response = await client.delete(f"{SECRETS_BASE}/openai")

    assert response.status_code == 404
