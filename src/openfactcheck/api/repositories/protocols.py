"""Repository protocol definitions for structural typing (Pyright strict)."""

from typing import Protocol

from openfactcheck.api.models import (
    Preferences,
    Project,
    ProjectCreate,
    ProjectUpdate,
    Secret,
    Workspace,
    WorkspaceCreate,
    WorkspaceRun,
    WorkspaceUpdate,
)


class ProjectRepository(Protocol):
    """Data access interface for projects."""

    async def list_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Project]:
        """List the user's projects, ordered by creation time (oldest first)."""
        ...

    async def get(self, user_id: str, project_id: str) -> Project | None:
        """Return the project, or ``None`` if no project with that ID exists for the user."""
        ...

    async def create(self, user_id: str, data: ProjectCreate) -> Project | None:
        """Create a new project for the user.

        Returns ``None`` if the user has already reached
        [`MAX_PROJECTS_PER_USER`][openfactcheck.api.repositories.constants.MAX_PROJECTS_PER_USER].
        """
        ...

    async def update(self, user_id: str, project_id: str, data: ProjectUpdate) -> Project | None:
        """Apply a partial update and return the updated project, or ``None`` if it doesn't exist.

        An update with no fields set returns the project unchanged.
        """
        ...

    async def delete(self, user_id: str, project_id: str) -> bool:
        """Delete the project and cascade-delete its workspaces and runs.

        Returns ``False`` if the project doesn't exist.
        """
        ...


class WorkspaceRepository(Protocol):
    """Data access interface for workspaces."""

    async def list_by_project(self, user_id: str, project_id: str) -> list[Workspace]:
        """List the project's workspaces, ordered by ``sort_order`` (display order)."""
        ...

    async def get(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None:
        """Return the workspace, or ``None`` if no workspace with that ID exists in the project."""
        ...

    async def create(self, user_id: str, project_id: str, data: WorkspaceCreate) -> Workspace | None:
        """Create a new workspace at the end of the project's sort order.

        Returns ``None`` if the project has already reached
        [`MAX_WORKSPACES_PER_PROJECT`][openfactcheck.api.repositories.constants.MAX_WORKSPACES_PER_PROJECT].
        """
        ...

    async def update(
        self,
        user_id: str,
        project_id: str,
        workspace_id: str,
        data: WorkspaceUpdate,
    ) -> Workspace | None:
        """Apply a partial update and return the updated workspace, or ``None`` if it doesn't exist.

        An update with no fields set returns the workspace unchanged.
        """
        ...

    async def delete(self, user_id: str, project_id: str, workspace_id: str) -> bool:
        """Delete the workspace. Returns ``False`` if it doesn't exist."""
        ...

    async def duplicate(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None:
        """Copy the workspace and append ``(copy)`` to its name.

        Returns ``None`` if the source workspace doesn't exist, or if the project has already reached
        [`MAX_WORKSPACES_PER_PROJECT`][openfactcheck.api.repositories.constants.MAX_WORKSPACES_PER_PROJECT].
        """
        ...

    async def reorder(self, user_id: str, project_id: str, ordered_ids: list[str]) -> None:
        """Reassign ``sort_order`` for the listed workspaces in the given sequence.

        Each ID in ``ordered_ids`` is numbered ``1..N``. IDs not in the list keep
        their current ``sort_order``.
        """
        ...

    async def set_run(self, user_id: str, project_id: str, workspace_id: str, run: WorkspaceRun) -> None:
        """Replace the workspace's latest run state with the given run."""
        ...


class SecretRepository(Protocol):
    """Data access interface for a user's encrypted secrets."""

    async def list(self, user_id: str) -> list[Secret]:
        """List the user's secrets (masked, no values), ordered by name."""
        ...

    async def set(self, user_id: str, name: str, ciphertext: str, hint: str) -> Secret | None:
        """Create or replace a secret's encrypted value.

        Returns ``None`` if storing a new secret would exceed
        [`MAX_SECRETS_PER_USER`][openfactcheck.api.repositories.constants.MAX_SECRETS_PER_USER];
        replacing an existing secret is always allowed.
        """
        ...

    async def get_ciphertext(self, user_id: str, name: str) -> str | None:
        """Return the stored ciphertext for a secret, or ``None`` if it is not set."""
        ...

    async def delete(self, user_id: str, name: str) -> bool:
        """Delete a secret. Returns ``False`` if it does not exist."""
        ...


class PreferencesRepository(Protocol):
    """Data access interface for a user's preferences."""

    async def get(self, user_id: str) -> Preferences:
        """Return the user's preferences, or an all-default record if none are stored."""
        ...

    async def set(self, user_id: str, preferences: Preferences) -> Preferences:
        """Replace the user's preferences with the given record."""
        ...
