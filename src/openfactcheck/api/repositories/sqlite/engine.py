"""SQLAlchemy async engine, session factory, and declarative base."""

import sqlite3
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM table models."""


def _resolve_url(sqlite_path: str) -> str:
    """Resolve the SQLite path and ensure the parent directory exists."""
    if sqlite_path == ":memory:":
        return "sqlite+aiosqlite:///:memory:"
    resolved = Path(sqlite_path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{resolved}"


def create_engine(sqlite_path: str) -> AsyncEngine:
    """Create an async SQLite engine with foreign key enforcement.

    Pass ``":memory:"`` for an in-memory database. Note: in-memory databases
    are not shared across connections and all data is lost when the engine
    is disposed. Use only for tests.
    """
    engine = create_async_engine(_resolve_url(sqlite_path))

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_conn: sqlite3.Connection, _connection_record: object) -> None:  # pyright: ignore[reportUnusedFunction] - registered via SQLAlchemy event listener.
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


async def create_tables(engine: AsyncEngine) -> None:
    """Create all tables defined on the declarative base."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return a session factory bound to *engine*."""
    return async_sessionmaker(engine, expire_on_commit=False)
