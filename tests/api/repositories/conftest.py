"""Shared fixtures for repository tests — in-memory SQLite engine and sessions."""

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openfactcheck.api.repositories.sqlite.engine import create_engine_and_tables, session_factory


@pytest_asyncio.fixture(loop_scope="function")
async def db_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Yield a session factory backed by a fresh in-memory SQLite database."""
    engine = await create_engine_and_tables(":memory:")
    factory = session_factory(engine)
    yield factory
    await engine.dispose()
