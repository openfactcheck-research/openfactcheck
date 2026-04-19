"""Workspace request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from openfactcheck.api.models import Workspace, WorkspaceSettings
from openfactcheck.api.models.types import JSONObject

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class CreateWorkspaceRequest(BaseModel):
    """Input payload for creating a workspace."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    name: str = Field(min_length=1, max_length=255)
    """Human-readable workspace name, 1 to 255 characters."""

    description: str = Field(default="", max_length=10000)
    """Freeform workspace description, up to 10000 characters."""


class UpdateWorkspaceRequest(BaseModel):
    """Input payload for partially updating a workspace."""

    model_config = ConfigDict(use_attribute_docstrings=True)

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


class ReorderWorkspacesRequest(BaseModel):
    """Input payload for reordering workspaces within a project."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    ordered_ids: list[Annotated[str, Field(max_length=20)]] = Field(min_length=1, max_length=5)
    """Workspace IDs in the desired display order. Must be a complete permutation of the project's workspaces."""


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class WorkspaceResponse(BaseModel):
    """Single workspace returned in API responses."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    id: str
    """Opaque unique identifier for the workspace."""

    project_id: str
    """Identifier of the project the workspace belongs to."""

    name: str
    """Human-readable workspace name."""

    description: str
    """Freeform workspace description."""

    locked: bool
    """When ``True``, the workspace is read-only."""

    sort_order: int
    """Ordering hint for display; lower values appear first."""

    settings: WorkspaceSettings
    """Workspace-level configuration."""

    content: JSONObject | None = None
    """Pipeline configuration as a JSON object. ``None`` for an empty workspace."""

    created_at: datetime
    """Timestamp the workspace was created."""

    updated_at: datetime
    """Timestamp of the most recent modification."""

    @staticmethod
    def from_model(ws: Workspace) -> WorkspaceResponse:
        """Convert a domain ``Workspace`` to a response schema."""
        return WorkspaceResponse(
            id=ws.id,
            project_id=ws.project_id,
            name=ws.name,
            description=ws.description,
            locked=ws.locked,
            sort_order=ws.sort_order,
            settings=ws.settings,
            content=ws.content,
            created_at=ws.created_at,
            updated_at=ws.updated_at,
        )
