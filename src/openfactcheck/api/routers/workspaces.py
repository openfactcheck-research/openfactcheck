"""Workspace CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from openfactcheck.api.dependencies import (
    get_current_user,
    get_workspace_repo,
)
from openfactcheck.api.errors import (
    AppError,
    ErrorCode,
    NotFoundError,
    WorkspaceLimitError,
)
from openfactcheck.api.models import (
    AuthUser,
    WorkspaceCreate,
    WorkspaceUpdate,
)
from openfactcheck.api.repositories.constants import MAX_CONTENT_BYTES
from openfactcheck.api.repositories.protocols import WorkspaceRepository
from openfactcheck.api.schemas.workspaces import (
    CreateWorkspaceRequest,
    ReorderWorkspacesRequest,
    UpdateWorkspaceRequest,
    WorkspaceResponse,
)

router = APIRouter(prefix="/projects/{project_id}/workspaces", tags=["workspaces"])

ResourceId = Annotated[str, Path(max_length=20)]


@router.get("")
async def list_workspaces(
    project_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> list[WorkspaceResponse]:
    """List all workspaces in a project."""
    workspaces = await repo.list_by_project(user.sub, project_id)
    return [WorkspaceResponse.from_model(ws) for ws in workspaces]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    project_id: ResourceId,
    body: CreateWorkspaceRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> WorkspaceResponse:
    """Create a new workspace in a project."""
    ws = await repo.create(
        user.sub,
        project_id,
        WorkspaceCreate(name=body.name, description=body.description),
    )
    if ws is None:
        raise WorkspaceLimitError
    return WorkspaceResponse.from_model(ws)


@router.get("/{workspace_id}")
async def get_workspace(
    project_id: ResourceId,
    workspace_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> WorkspaceResponse:
    """Get a single workspace by ID."""
    ws = await repo.get(user.sub, project_id, workspace_id)
    if ws is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")
    return WorkspaceResponse.from_model(ws)


@router.patch("/{workspace_id}")
async def update_workspace(
    project_id: ResourceId,
    workspace_id: ResourceId,
    body: UpdateWorkspaceRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> WorkspaceResponse:
    """Update a workspace."""
    if body.content is not None and len(str(body.content)) > MAX_CONTENT_BYTES:
        raise AppError(
            "Workspace content exceeds size limit",
            ErrorCode.VALIDATION_ERROR,
            status=422,
        )
    ws = await repo.update(
        user.sub,
        project_id,
        workspace_id,
        WorkspaceUpdate(
            name=body.name,
            description=body.description,
            locked=body.locked,
            settings=body.settings,
            content=body.content,
        ),
    )
    if ws is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")
    return WorkspaceResponse.from_model(ws)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    project_id: ResourceId,
    workspace_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> None:
    """Delete a workspace."""
    deleted = await repo.delete(user.sub, project_id, workspace_id)
    if not deleted:
        raise NotFoundError(f"Workspace {workspace_id} not found")


@router.post("/{workspace_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_workspace(
    project_id: ResourceId,
    workspace_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> WorkspaceResponse:
    """Duplicate a workspace."""
    # Check if source exists before attempting duplicate
    source = await repo.get(user.sub, project_id, workspace_id)
    if source is None:
        raise NotFoundError(f"Workspace {workspace_id} not found")

    ws = await repo.duplicate(user.sub, project_id, workspace_id)
    if ws is None:
        raise WorkspaceLimitError
    return WorkspaceResponse.from_model(ws)


@router.put("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_workspaces(
    project_id: ResourceId,
    body: ReorderWorkspacesRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
) -> None:
    """Reorder workspaces in a project. ordered_ids must be a complete permutation."""
    current = await repo.list_by_project(user.sub, project_id)
    current_ids = {ws.id for ws in current}
    submitted_ids = set(body.ordered_ids)

    if len(body.ordered_ids) != len(submitted_ids):
        raise AppError("ordered_ids contains duplicates", ErrorCode.VALIDATION_ERROR, status=422)
    if submitted_ids != current_ids:
        raise AppError(
            "ordered_ids must contain exactly all workspace IDs",
            ErrorCode.VALIDATION_ERROR,
            status=422,
        )

    await repo.reorder(user.sub, project_id, body.ordered_ids)
