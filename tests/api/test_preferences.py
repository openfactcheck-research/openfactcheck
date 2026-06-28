"""Tests for user preferences endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="function")

PREFERENCES_BASE = "/api/v1/preferences"


async def test_get_preferences_defaults(client: AsyncClient) -> None:
    """GET returns all-default preferences for a user who has set none."""
    response = await client.get(f"{PREFERENCES_BASE}/")

    assert response.status_code == 200
    assert response.json() == {"tour_completed": False}


async def test_update_preferences(client: AsyncClient) -> None:
    """PUT replaces and returns the user's preferences."""
    response = await client.put(f"{PREFERENCES_BASE}/", json={"tour_completed": True})

    assert response.status_code == 200
    assert response.json() == {"tour_completed": True}


async def test_update_preferences_persists(client: AsyncClient) -> None:
    """A later GET returns the preferences set by a prior PUT."""
    await client.put(f"{PREFERENCES_BASE}/", json={"tour_completed": True})

    response = await client.get(f"{PREFERENCES_BASE}/")

    assert response.json() == {"tour_completed": True}
