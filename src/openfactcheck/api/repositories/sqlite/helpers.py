"""Shared helpers for SQLite repository implementations."""

from datetime import UTC, datetime


def ensure_utc(dt: datetime) -> datetime:
    """Attach UTC tzinfo to a naive datetime from SQLite."""
    return dt.replace(tzinfo=UTC)


def ensure_utc_optional(dt: datetime | None) -> datetime | None:
    """Attach UTC tzinfo to an optional naive datetime from SQLite."""
    return dt.replace(tzinfo=UTC) if dt else None
