"""Project request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from openfactcheck.api.models import Project


class CreateProjectRequest(BaseModel):
    """Body for POST /api/v1/projects."""

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)


class UpdateProjectRequest(BaseModel):
    """Body for PATCH /api/v1/projects/{id}."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)


class ProjectResponse(BaseModel):
    """Single project in API responses."""

    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_model(project: Project) -> ProjectResponse:
        """Convert a domain Project to a response schema."""
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
