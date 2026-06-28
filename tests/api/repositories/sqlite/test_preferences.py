"""Tests for SqlitePreferencesRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import Preferences
from openfactcheck.api.repositories.sqlite.preferences import SqlitePreferencesRepository

USER_ID = "user-1"
OTHER_USER = "user-2"

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest.fixture
def repo(db_session_factory: async_sessionmaker[AsyncSession]) -> SqlitePreferencesRepository:
    return SqlitePreferencesRepository(db_session_factory)


async def test_SqlitePreferencesRepository_get_returns_defaults_when_unset(repo: SqlitePreferencesRepository) -> None:
    """An unset user reads as an all-default preferences record."""
    assert await repo.get(USER_ID) == Preferences(tour_completed=False)


async def test_SqlitePreferencesRepository_set_persists(repo: SqlitePreferencesRepository) -> None:
    """Set stores preferences that a later get returns."""
    await repo.set(USER_ID, Preferences(tour_completed=True))

    assert (await repo.get(USER_ID)).tour_completed is True


async def test_SqlitePreferencesRepository_set_replaces(repo: SqlitePreferencesRepository) -> None:
    """A second set replaces the stored preferences."""
    await repo.set(USER_ID, Preferences(tour_completed=True))
    await repo.set(USER_ID, Preferences(tour_completed=False))

    assert (await repo.get(USER_ID)).tour_completed is False


async def test_SqlitePreferencesRepository_scopes_to_user(repo: SqlitePreferencesRepository) -> None:
    """Preferences are isolated per user."""
    await repo.set(USER_ID, Preferences(tour_completed=True))

    assert (await repo.get(OTHER_USER)).tour_completed is False
