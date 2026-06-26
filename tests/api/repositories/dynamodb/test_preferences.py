"""Tests for DynamoPreferencesRepository."""

import pytest

from openfactcheck.api.models import Preferences
from openfactcheck.api.repositories.dynamodb.preferences import DynamoPreferencesRepository

USER_ID = "user-1"
OTHER_USER = "user-2"
REGION = "us-east-1"

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest.fixture
def repo(dynamo_table: str) -> DynamoPreferencesRepository:
    return DynamoPreferencesRepository(dynamo_table, region_name=REGION)


async def test_DynamoPreferencesRepository_get_returns_defaults_when_unset(repo: DynamoPreferencesRepository) -> None:
    """An unset user reads as an all-default preferences record."""
    assert await repo.get(USER_ID) == Preferences(tour_completed=False)


async def test_DynamoPreferencesRepository_set_persists(repo: DynamoPreferencesRepository) -> None:
    """Set stores preferences that a later get returns."""
    await repo.set(USER_ID, Preferences(tour_completed=True))

    assert (await repo.get(USER_ID)).tour_completed is True


async def test_DynamoPreferencesRepository_set_replaces(repo: DynamoPreferencesRepository) -> None:
    """A second set replaces the stored preferences."""
    await repo.set(USER_ID, Preferences(tour_completed=True))
    await repo.set(USER_ID, Preferences(tour_completed=False))

    assert (await repo.get(USER_ID)).tour_completed is False


async def test_DynamoPreferencesRepository_scopes_to_user(repo: DynamoPreferencesRepository) -> None:
    """Preferences are isolated per user."""
    await repo.set(USER_ID, Preferences(tour_completed=True))

    assert (await repo.get(OTHER_USER)).tour_completed is False
