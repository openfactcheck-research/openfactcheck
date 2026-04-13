"""Project CRUD endpoints — /api/v1/projects."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from openfactcheck.api.dependencies import get_current_user, get_project_repo
from openfactcheck.api.errors import NotFoundError, ProjectLimitError
from openfactcheck.api.models import AuthUser, ProjectCreate, ProjectUpdate
from openfactcheck.api.repositories.protocols import ProjectRepository
from openfactcheck.api.schemas.projects import CreateProjectRequest, ProjectResponse, UpdateProjectRequest

router = APIRouter(prefix="/projects", tags=["projects"])

ResourceId = Annotated[str, Path(max_length=20)]


@router.get("/")
async def list_projects(
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProjectResponse]:
    """List all projects for the current user."""
    projects = await repo.list_by_user(user.sub, limit=limit, offset=offset)
    return [ProjectResponse.from_model(p) for p in projects]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(
    body: CreateProjectRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> ProjectResponse:
    """Create a new project."""
    project = await repo.create(user.sub, ProjectCreate(name=body.name, description=body.description))
    if project is None:
        raise ProjectLimitError()
    return ProjectResponse.from_model(project)


@router.get("/{project_id}")
async def get_project(
    project_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> ProjectResponse:
    """Get a single project by ID."""
    project = await repo.get(user.sub, project_id)
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    return ProjectResponse.from_model(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: ResourceId,
    body: UpdateProjectRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> ProjectResponse:
    """Update a project."""
    project = await repo.update(user.sub, project_id, ProjectUpdate(name=body.name, description=body.description))
    if project is None:
        raise NotFoundError(f"Project {project_id} not found")
    return ProjectResponse.from_model(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: ResourceId,
    user: Annotated[AuthUser, Depends(get_current_user)],
    repo: Annotated[ProjectRepository, Depends(get_project_repo)],
) -> None:
    """Delete a project."""
    deleted = await repo.delete(user.sub, project_id)
    if not deleted:
        raise NotFoundError(f"Project {project_id} not found")
