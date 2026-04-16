"""Project domain model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from openfactcheck.api.models.validators import normalize_datetime, to_camel

# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class Project(BaseModel):
    """A user's fact-checking project."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    id: str
    user_id: str
    name: str
    description: str = ""
    created_at: datetime
    updated_at: datetime

    _normalize_datetime = field_validator("created_at", "updated_at", mode="before")(normalize_datetime)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    """Fields required to create a new project."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)


class ProjectUpdate(BaseModel):
    """Fields that can be updated on a project. All optional."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
