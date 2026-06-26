"""User secret domain model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from openfactcheck.api.models.validators import normalize_datetime, to_camel

SECRET_NAME_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"  # noqa: S105 - regex for secret names, not a credential.
"""Allowed secret names: a leading lowercase letter, then lowercase letters, digits, or underscores, up to 64 chars."""


class Secret(BaseModel):
    """A stored user secret, returned without its value.

    The raw value is never exposed once set; only a short hint of its trailing
    characters comes back, enough to recognize which key is stored.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        use_attribute_docstrings=True,
    )

    name: str
    """Identifier for the secret, for example ``"openai"``."""

    hint: str = ""
    """Trailing characters of the value, shown so the user can recognize the stored key."""

    created_at: datetime
    """Timestamp the secret was first set."""

    updated_at: datetime
    """Timestamp of the most recent change."""

    _normalize_datetime = field_validator("created_at", "updated_at", mode="before")(normalize_datetime)
