"""Workspace request/response schemas."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from openfactcheck.api.models import Workspace, WorkspaceSettings


class CreateWorkspaceRequest(BaseModel):
    """Body for POST /api/v1/projects/{pid}/workspaces."""

    name: str = Field(min_length=1, max_length=255)


class UpdateWorkspaceRequest(BaseModel):
    """Body for PATCH /api/v1/projects/{pid}/workspaces/{wid}."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    locked: bool | None = None
    settings: WorkspaceSettings | None = None


class ReorderWorkspacesRequest(BaseModel):
    """Body for PUT /api/v1/projects/{pid}/workspaces/reorder."""

    ordered_ids: list[Annotated[str, Field(max_length=20)]] = Field(min_length=1, max_length=5)


class WorkspaceResponse(BaseModel):
    """Single workspace in API responses."""

    id: str
    project_id: str
    name: str
    description: str
    locked: bool
    sort_order: int
    settings: WorkspaceSettings
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def from_model(ws: Workspace) -> "WorkspaceResponse":
        """Convert a domain Workspace to a response schema."""
        return WorkspaceResponse(
            id=ws.id,
            project_id=ws.project_id,
            name=ws.name,
            description=ws.description,
            locked=ws.locked,
            sort_order=ws.sort_order,
            settings=ws.settings,
            created_at=ws.created_at,
            updated_at=ws.updated_at,
        )
