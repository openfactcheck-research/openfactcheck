"""Repository protocol definitions for structural typing (Pyright strict)."""

from typing import Protocol

from openfactcheck.api.models import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    Workspace,
    WorkspaceCreate,
    WorkspaceRun,
    WorkspaceUpdate,
)


class ProjectRepository(Protocol):
    """Data access interface for projects."""

    async def list_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Project]: ...

    async def get(self, user_id: str, project_id: str) -> Project | None: ...

    async def create(self, user_id: str, data: ProjectCreate) -> Project | None: ...

    async def update(self, user_id: str, project_id: str, data: ProjectUpdate) -> Project | None: ...

    async def delete(self, user_id: str, project_id: str) -> bool: ...


class WorkspaceRepository(Protocol):
    """Data access interface for workspaces."""

    async def list_by_project(self, user_id: str, project_id: str) -> list[Workspace]: ...

    async def get(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None: ...

    async def create(self, user_id: str, project_id: str, data: WorkspaceCreate) -> Workspace | None: ...

    async def update(
        self, user_id: str, project_id: str, workspace_id: str, data: WorkspaceUpdate
    ) -> Workspace | None: ...

    async def delete(self, user_id: str, project_id: str, workspace_id: str) -> bool: ...

    async def duplicate(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None: ...

    async def reorder(self, user_id: str, project_id: str, ordered_ids: list[str]) -> None: ...

    async def set_run(self, user_id: str, project_id: str, workspace_id: str, run: WorkspaceRun) -> None: ...
