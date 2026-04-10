"""Run domain model."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    """Lifecycle states for a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(BaseModel):
    """A single execution of a pipeline within a project."""

    id: str
    user_id: str
    project_id: str
    workspace_id: str
    status: RunStatus
    pipeline: dict[str, object]
    output: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RunCreate(BaseModel):
    """Fields required to create a new run."""

    workspace_id: str = Field(max_length=20)
    pipeline: dict[str, object]
