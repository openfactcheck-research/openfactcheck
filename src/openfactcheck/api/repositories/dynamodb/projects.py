"""DynamoDB-backed project repository."""

from datetime import UTC, datetime

from openfactcheck.api.models import Project, ProjectCreate, ProjectUpdate
from openfactcheck.api.repositories.constants import MAX_PROJECTS_PER_USER, generate_id
from openfactcheck.api.repositories.dynamodb.base import BaseDynamoRepository
from openfactcheck.api.repositories.dynamodb.keys import (
    project_pk,
    project_sk,
    workspace_pk,
)
from openfactcheck.api.repositories.dynamodb.types import DynamoItem


class DynamoProjectRepository(BaseDynamoRepository):
    """DynamoDB-backed repository for project CRUD."""

    async def list_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Project]:
        """List the user's projects, ordered by creation time (oldest first)."""
        items = await self._query_by_pk(project_pk(user_id), sk_prefix="PROJECT#")
        projects = sorted((Project.model_validate(item) for item in items), key=lambda p: p.created_at)
        return projects[offset : offset + limit]

    async def get(self, user_id: str, project_id: str) -> Project | None:
        """Return the project, or ``None`` if no project with that ID exists for the user."""
        item = await self._get(project_pk(user_id), project_sk(project_id))
        return Project.model_validate(item) if item else None

    async def create(self, user_id: str, data: ProjectCreate) -> Project | None:
        """Create a new project for the user.

        Returns ``None`` if the user has already reached [`MAX_PROJECTS_PER_USER`][MAX_PROJECTS_PER_USER].
        """
        items = await self._query_by_pk(project_pk(user_id), sk_prefix="PROJECT#")
        if len(items) >= MAX_PROJECTS_PER_USER:
            return None

        now = datetime.now(UTC)
        pid = generate_id()
        item: DynamoItem = {
            "PK": project_pk(user_id),
            "SK": project_sk(pid),
            "id": pid,
            "userId": user_id,
            "name": data.name,
            "description": data.description,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        await self._put(item)
        return Project.model_validate(item)

    async def update(self, user_id: str, project_id: str, data: ProjectUpdate) -> Project | None:
        """Apply a partial update and return the updated project, or ``None`` if it doesn't exist.

        An update with no fields set returns the project unchanged.
        """
        values = data.model_dump(exclude_none=True)
        if not values:
            return await self.get(user_id, project_id)

        attrs = await self._update(project_pk(user_id), project_sk(project_id), values)
        return Project.model_validate(attrs) if attrs else None

    async def delete(self, user_id: str, project_id: str) -> bool:
        """Delete the project and cascade-delete its workspaces.

        Returns ``False`` if the project doesn't exist.
        """
        deleted = await self._delete(project_pk(user_id), project_sk(project_id))
        if not deleted:
            return False

        # Cascade: delete every child workspace under this project.
        children = await self._query_by_pk(workspace_pk(user_id, project_id), projection="PK, SK")
        if children:
            await self._batch_delete(children)

        return True
