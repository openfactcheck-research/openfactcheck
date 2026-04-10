"""Project domain model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Project(BaseModel):
    """A user's fact-checking project."""

    id: str
    user_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    """Fields required to create a new project."""

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)


class ProjectUpdate(BaseModel):
    """Fields that can be updated on a project. All optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
