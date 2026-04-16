"""Shared Pydantic validators and config helpers for model fields."""

from datetime import UTC, datetime


def to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def normalize_datetime(v: datetime | str) -> datetime:
    """Parse ISO strings and ensure all datetimes are UTC."""
    dt = datetime.fromisoformat(v) if isinstance(v, str) else v
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_datetime_optional(v: datetime | str | None) -> datetime | None:
    """Parse ISO strings and ensure all datetimes are UTC. Accepts None."""
    if v is None:
        return None
    return normalize_datetime(v)
