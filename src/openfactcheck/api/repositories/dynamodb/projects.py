# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""DynamoDB implementation of the project repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from openfactcheck.api.models import Project, ProjectCreate, ProjectUpdate
from openfactcheck.api.repositories.constants import MAX_PROJECTS_PER_USER, generate_id
from openfactcheck.api.repositories.dynamodb.base import BaseDynamoRepository
from openfactcheck.api.repositories.dynamodb.keys import project_pk, project_sk, workspace_pk


def _item_to_model(item: dict[str, Any]) -> Project:
    return Project(
        id=item["id"],
        user_id=item["userId"],
        name=item["name"],
        description=item.get("description", ""),
        created_at=datetime.fromisoformat(item["createdAt"]),
        updated_at=datetime.fromisoformat(item["updatedAt"]),
    )


class DynamoProjectRepository(BaseDynamoRepository):
    """Project CRUD backed by DynamoDB single-table design."""

    async def list_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Project]:
        items = await self._query_by_pk(project_pk(user_id), sk_prefix="PROJECT#")
        projects = sorted((_item_to_model(item) for item in items), key=lambda p: p.created_at)
        return projects[offset : offset + limit]

    async def get(self, user_id: str, project_id: str) -> Project | None:
        item = await self._get(project_pk(user_id), project_sk(project_id))
        return _item_to_model(item) if item else None

    async def create(self, user_id: str, data: ProjectCreate) -> Project | None:
        items = await self._query_by_pk(project_pk(user_id), sk_prefix="PROJECT#")
        if len(items) >= MAX_PROJECTS_PER_USER:
            return None

        now = datetime.now(UTC)
        pid = generate_id()
        item: dict[str, Any] = {
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
        return _item_to_model(item)

    async def update(self, user_id: str, project_id: str, data: ProjectUpdate) -> Project | None:
        values = data.model_dump(exclude_none=True)
        if not values:
            return await self.get(user_id, project_id)

        attrs = await self._update(project_pk(user_id), project_sk(project_id), values)
        return _item_to_model(attrs) if attrs else None

    async def delete(self, user_id: str, project_id: str) -> bool:
        deleted = await self._delete(project_pk(user_id), project_sk(project_id))
        if not deleted:
            return False

        # Cascade — delete all child items (workspaces + runs) belonging to this project
        children = await self._query_by_pk(workspace_pk(user_id, project_id), projection="PK, SK")
        if children:
            await self._batch_delete(children)

        return True
