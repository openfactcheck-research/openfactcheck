"""SQLAlchemy async engine, session factory, and declarative base."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM table models."""


async def create_engine_and_tables(sqlite_path: str) -> AsyncEngine:
    """Create an async SQLite engine and ensure all tables exist.

    The parent directory for *sqlite_path* is created if it does not exist.
    Pass ``":memory:"`` for an in-memory database (useful in tests).
    """
    if sqlite_path != ":memory:":
        resolved = Path(sqlite_path).expanduser().resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite+aiosqlite:///{resolved}"
    else:
        url = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(url)

    # Enable foreign key enforcement (required for CASCADE to work in SQLite)
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_conn: object, _connection_record: object) -> None:  # pyright: ignore[reportUnusedFunction]
        cursor = dbapi_conn.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA foreign_keys=ON")  # type: ignore[union-attr]
        cursor.close()  # type: ignore[union-attr]

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return a session factory bound to *engine*."""
    return async_sessionmaker(engine, expire_on_commit=False)
