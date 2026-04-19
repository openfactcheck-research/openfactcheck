"""Project domain model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from openfactcheck.api.models.validators import normalize_datetime, to_camel

# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class Project(BaseModel):
    """A user's fact-checking project."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        use_attribute_docstrings=True,
    )

    id: str
    """Opaque unique identifier for the project."""

    user_id: str
    """Identifier of the user who owns the project."""

    name: str
    """Human-readable project name."""

    description: str = ""
    """Freeform project description."""

    created_at: datetime
    """Timestamp the project was created."""

    updated_at: datetime
    """Timestamp of the most recent modification."""

    _normalize_datetime = field_validator("created_at", "updated_at", mode="before")(normalize_datetime)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    """Fields required to create a new project."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_attribute_docstrings=True,
    )

    name: str = Field(min_length=1, max_length=255)
    """Human-readable project name, 1 to 255 characters."""

    description: str = Field(default="", max_length=10000)
    """Freeform project description, up to 10000 characters."""


class ProjectUpdate(BaseModel):
    """Fields that can be updated on a project. All optional."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_attribute_docstrings=True,
    )

    name: str | None = Field(default=None, min_length=1, max_length=255)
    """New project name, 1 to 255 characters. ``None`` leaves the existing name unchanged."""

    description: str | None = Field(default=None, max_length=10000)
    """New description, up to 10000 characters. ``None`` leaves the existing description unchanged."""
