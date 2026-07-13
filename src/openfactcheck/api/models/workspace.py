"""Workspace domain model."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from openfactcheck.api.models.types import JSONObject, JSONString, JSONValue
from openfactcheck.api.models.validators import normalize_datetime, to_camel

# ---------------------------------------------------------------------------
# WorkspaceSettings
# ---------------------------------------------------------------------------


class WorkspaceSettings(BaseModel):
    """Optional per-workspace configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_attribute_docstrings=True,
    )

    verbose_mode: bool = False
    """Emit verbose execution logs during pipeline runs."""


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


class Workspace(BaseModel):
    """A workspace within a project, containing a single pipeline configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        use_attribute_docstrings=True,
    )

    id: str
    """Opaque unique identifier for the workspace."""

    user_id: str
    """Identifier of the user who owns the workspace."""

    project_id: str
    """Identifier of the project the workspace belongs to."""

    name: str
    """Human-readable workspace name."""

    description: str = ""
    """Freeform workspace description."""

    locked: bool = False
    """When ``True``, the workspace is read-only."""

    sort_order: int = 0
    """Ordering hint for display; lower values appear first."""

    settings: WorkspaceSettings = Field(
        default_factory=WorkspaceSettings,
        validation_alias=AliasChoices("settings", "settings_json"),
    )
    """Workspace-level configuration."""

    content: JSONObject | None = Field(
        default=None,
        validation_alias=AliasChoices("content", "content_json"),
    )
    """Pipeline configuration as a JSON object. ``None`` for an empty workspace."""

    created_at: datetime
    """Timestamp the workspace was created."""

    updated_at: datetime
    """Timestamp of the most recent modification."""

    _normalize_datetime = field_validator("created_at", "updated_at", mode="before")(normalize_datetime)

    @field_validator("settings", mode="before")
    @classmethod
    def _parse_settings(cls, v: JSONString | JSONObject | WorkspaceSettings) -> WorkspaceSettings:
        if isinstance(v, str):
            return WorkspaceSettings.model_validate_json(v)
        if isinstance(v, dict):
            return WorkspaceSettings.model_validate(v)
        return v

    @field_validator("content", mode="before")
    @classmethod
    def _parse_content(cls, v: JSONString | JSONObject | None) -> JSONObject | None:
        if isinstance(v, str):
            parsed: JSONValue = json.loads(v)
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected JSON object, got {type(parsed).__name__}")  # noqa: TRY004 - Pydantic validators must raise ValueError.
            return parsed
        return v


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


class WorkspaceCreate(BaseModel):
    """Fields required to create a new workspace."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_attribute_docstrings=True,
    )

    name: str = Field(min_length=1, max_length=255)
    """Human-readable workspace name, 1 to 255 characters."""

    description: str = Field(default="", max_length=10000)
    """Freeform workspace description, up to 10000 characters."""


class WorkspaceUpdate(BaseModel):
    """Fields that can be updated on a workspace. All optional."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_attribute_docstrings=True,
    )

    name: str | None = Field(default=None, min_length=1, max_length=255)
    """New workspace name, 1 to 255 characters. ``None`` leaves the existing name unchanged."""

    description: str | None = Field(default=None, max_length=10000)
    """New description, up to 10000 characters. ``None`` leaves the existing description unchanged."""

    locked: bool | None = None
    """New lock state. ``None`` leaves the existing value unchanged."""

    settings: WorkspaceSettings | None = None
    """Replacement settings. ``None`` leaves the existing settings unchanged."""

    content: JSONObject | None = None
    """Replacement pipeline configuration. ``None`` leaves the existing content unchanged."""
