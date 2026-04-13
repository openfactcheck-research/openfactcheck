"""Workspace domain model."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    """Lifecycle states for a pipeline run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkspaceRun(BaseModel):
    """Latest pipeline run state for a workspace."""

    status: RunStatus
    output: str = ""
    error: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkspaceSettings(BaseModel):
    """Optional per-workspace configuration."""

    verbose_mode: bool = False


class Workspace(BaseModel):
    """A workspace within a project, containing a single pipeline configuration."""

    id: str
    user_id: str
    project_id: str
    name: str
    description: str = ""
    locked: bool = False
    sort_order: int
    settings: WorkspaceSettings = Field(default_factory=WorkspaceSettings)
    content: dict[str, object] | None = None
    run: WorkspaceRun | None = None
    created_at: datetime
    updated_at: datetime


class WorkspaceCreate(BaseModel):
    """Fields required to create a new workspace."""

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)


class WorkspaceUpdate(BaseModel):
    """Fields that can be updated on a workspace. All optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    locked: bool | None = None
    settings: WorkspaceSettings | None = None
    content: dict[str, object] | None = None
