"""Workspace domain model."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from openfactcheck.api.models.types import JSONObject, JSONString, JSONValue
from openfactcheck.api.models.validators import normalize_datetime, normalize_datetime_optional, to_camel

# ---------------------------------------------------------------------------
# WorkspaceRun
# ---------------------------------------------------------------------------


class WorkspaceRunStatus(StrEnum):
    """Lifecycle states for a pipeline run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkspaceRun(BaseModel):
    """Latest pipeline run state for a workspace."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    status: WorkspaceRunStatus
    output: str = ""
    error: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None

    _normalize_datetime = field_validator("started_at", "completed_at", mode="before")(normalize_datetime_optional)

    def _check_running(self) -> None:
        if self.started_at is None:
            raise ValueError("Running run must have started_at")
        if self.completed_at is not None:
            raise ValueError("Running run must not have completed_at")
        if self.error:
            raise ValueError("Running run must not have error")

    def _check_completed(self) -> None:
        if self.completed_at is None:
            raise ValueError("Completed run must have completed_at")
        if self.error:
            raise ValueError("Completed run must not have error")

    def _check_failed(self) -> None:
        if self.completed_at is None:
            raise ValueError("Failed run must have completed_at")
        if not self.error:
            raise ValueError("Failed run must have error")

    @model_validator(mode="after")
    def _check_state_invariants(self) -> WorkspaceRun:
        match self.status:
            case WorkspaceRunStatus.RUNNING:
                self._check_running()
            case WorkspaceRunStatus.COMPLETED:
                self._check_completed()
            case WorkspaceRunStatus.FAILED:
                self._check_failed()

        if self.started_at and self.completed_at and self.completed_at < self.started_at:
            raise ValueError("completed_at must be >= started_at")

        return self


# ---------------------------------------------------------------------------
# WorkspaceSettings
# ---------------------------------------------------------------------------


class WorkspaceSettings(BaseModel):
    """Optional per-workspace configuration."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    verbose_mode: bool = False


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


class Workspace(BaseModel):
    """A workspace within a project, containing a single pipeline configuration."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    id: str
    user_id: str
    project_id: str
    name: str
    description: str = ""
    locked: bool = False
    sort_order: int = 0
    settings: WorkspaceSettings = Field(
        default_factory=WorkspaceSettings, validation_alias=AliasChoices("settings", "settings_json")
    )
    content: JSONObject | None = Field(default=None, validation_alias=AliasChoices("content", "content_json"))
    run: WorkspaceRun | None = Field(default=None, validation_alias=AliasChoices("run", "run_json"))
    created_at: datetime
    updated_at: datetime

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

    @field_validator("run", mode="before")
    @classmethod
    def _parse_run(cls, v: JSONString | JSONObject | WorkspaceRun | None) -> WorkspaceRun | None:
        if isinstance(v, str):
            return WorkspaceRun.model_validate_json(v)
        if isinstance(v, dict):
            return WorkspaceRun.model_validate(v)
        return v


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


class WorkspaceCreate(BaseModel):
    """Fields required to create a new workspace."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)


class WorkspaceUpdate(BaseModel):
    """Fields that can be updated on a workspace. All optional."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    locked: bool | None = None
    settings: WorkspaceSettings | None = None
    content: JSONObject | None = None
