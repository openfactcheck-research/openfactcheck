"""Repository protocol definitions for structural typing (Pyright strict)."""

from __future__ import annotations

from typing import Protocol

from openfactcheck.api.models import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    Run,
    RunCreate,
    RunStatus,
    Workspace,
    WorkspaceCreate,
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


class RunRepository(Protocol):
    """Data access interface for pipeline runs."""

    async def create(self, user_id: str, project_id: str, data: RunCreate) -> Run: ...

    async def get(self, user_id: str, project_id: str, run_id: str) -> Run | None: ...

    async def update_status(
        self,
        user_id: str,
        project_id: str,
        run_id: str,
        status: RunStatus,
        output: str | None = None,
        error: str | None = None,
    ) -> Run | None: ...

    async def list_by_project(
        self,
        user_id: str,
        project_id: str,
        workspace_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Run]: ...
