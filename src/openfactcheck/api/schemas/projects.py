"""Project request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from openfactcheck.api.models import Project

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    """Input payload for creating a project."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(min_length=1, max_length=255)
    """Human-readable project name, 1 to 255 characters."""

    description: str = Field(default="", max_length=10000)
    """Freeform project description, up to 10000 characters."""


class UpdateProjectRequest(BaseModel):
    """Input payload for partially updating a project."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    """New project name, 1 to 255 characters. ``None`` leaves the existing name unchanged."""

    description: str | None = Field(default=None, max_length=10000)
    """New description, up to 10000 characters. ``None`` leaves the existing description unchanged."""


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ProjectResponse(BaseModel):
    """Single project returned in API responses."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    id: str
    """Opaque unique identifier for the project."""

    name: str
    """Human-readable project name."""

    description: str
    """Freeform project description."""

    created_at: datetime
    """Timestamp the project was created."""

    updated_at: datetime
    """Timestamp of the most recent modification."""

    @staticmethod
    def from_model(project: Project) -> ProjectResponse:
        """Convert a domain ``Project`` to a response schema."""
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
