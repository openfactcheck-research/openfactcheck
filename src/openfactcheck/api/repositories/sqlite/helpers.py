"""Shared helpers for SQLite repository implementations."""

from openfactcheck.api.repositories.sqlite.engine import Base


def row_to_dict(row: Base) -> dict[str, object]:
    """Extract mapped column values from an ORM row, excluding ORM internals."""
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}
