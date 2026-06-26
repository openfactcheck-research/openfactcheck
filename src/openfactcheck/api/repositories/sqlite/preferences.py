"""SQLite-backed user preferences repository."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.models import Preferences
from openfactcheck.api.repositories.sqlite.tables import PreferencesRow


class SqlitePreferencesRepository:
    """SQLite-backed repository for a user's preferences."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Build a repository that opens sessions from the given factory.

        Args:
            session_factory: Async session factory bound to a SQLite engine.
        """
        self._session_factory = session_factory

    async def get(self, user_id: str) -> Preferences:
        """Return the user's preferences, or an all-default record if none are stored."""
        async with self._session_factory() as session:
            row = await session.get(PreferencesRow, user_id)
            return Preferences.model_validate_json(row.data_json) if row else Preferences()

    async def set(self, user_id: str, preferences: Preferences) -> Preferences:
        """Replace the user's preferences with the given record."""
        data = preferences.model_dump_json()
        async with self._session_factory() as session:
            row = await session.get(PreferencesRow, user_id)
            if row is None:
                session.add(PreferencesRow(user_id=user_id, data_json=data))
            else:
                row.data_json = data
            await session.commit()
        return preferences
