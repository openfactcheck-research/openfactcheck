"""DynamoDB implementation of the workspace repository."""

import asyncio
from datetime import UTC, datetime

from openfactcheck.api.models import (
    Workspace,
    WorkspaceCreate,
    WorkspaceRun,
    WorkspaceUpdate,
)
from openfactcheck.api.repositories.constants import (
    MAX_WORKSPACES_PER_PROJECT,
    generate_id,
)
from openfactcheck.api.repositories.dynamodb.base import BaseDynamoRepository
from openfactcheck.api.repositories.dynamodb.keys import workspace_pk, workspace_sk
from openfactcheck.api.repositories.dynamodb.types import DynamoItem


class DynamoWorkspaceRepository(BaseDynamoRepository):
    """Workspace CRUD backed by DynamoDB single-table design."""

    async def _list_items(self, user_id: str, project_id: str) -> list[DynamoItem]:
        return await self._query_by_pk(workspace_pk(user_id, project_id), sk_prefix="WORKSPACE#")

    async def list_by_project(self, user_id: str, project_id: str) -> list[Workspace]:
        items = await self._list_items(user_id, project_id)
        workspaces = [Workspace.model_validate(item) for item in items]
        return sorted(workspaces, key=lambda w: w.sort_order)

    async def get(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None:
        item = await self._get(workspace_pk(user_id, project_id), workspace_sk(workspace_id))
        return Workspace.model_validate(item) if item else None

    async def create(self, user_id: str, project_id: str, data: WorkspaceCreate) -> Workspace | None:
        items = await self._list_items(user_id, project_id)
        if len(items) >= MAX_WORKSPACES_PER_PROJECT:
            return None

        max_order = max((int(i.get("sortOrder", 0)) for i in items), default=0)

        now = datetime.now(UTC)
        wid = generate_id()
        item: DynamoItem = {
            "PK": workspace_pk(user_id, project_id),
            "SK": workspace_sk(wid),
            "id": wid,
            "userId": user_id,
            "projectId": project_id,
            "name": data.name,
            "description": data.description,
            "locked": False,
            "sortOrder": max_order + 1,
            "settings": {},
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        await self._put(item)
        return Workspace.model_validate(item)

    async def update(self, user_id: str, project_id: str, workspace_id: str, data: WorkspaceUpdate) -> Workspace | None:
        values: DynamoItem = {}
        if data.name is not None:
            values["name"] = data.name
        if data.description is not None:
            values["description"] = data.description
        if data.locked is not None:
            values["locked"] = data.locked
        if data.settings is not None:
            values["settings"] = data.settings.model_dump()
        if data.content is not None:
            values["content"] = data.content

        if not values:
            return await self.get(user_id, project_id, workspace_id)

        attrs = await self._update(workspace_pk(user_id, project_id), workspace_sk(workspace_id), values)
        return Workspace.model_validate(attrs) if attrs else None

    async def delete(self, user_id: str, project_id: str, workspace_id: str) -> bool:
        return await self._delete(workspace_pk(user_id, project_id), workspace_sk(workspace_id))

    async def duplicate(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None:
        source = await self.get(user_id, project_id, workspace_id)
        if source is None:
            return None

        items = await self._list_items(user_id, project_id)
        if len(items) >= MAX_WORKSPACES_PER_PROJECT:
            return None

        max_order = max((int(i.get("sortOrder", 0)) for i in items), default=0)

        now = datetime.now(UTC)
        new_id = generate_id()
        item: DynamoItem = {
            "PK": workspace_pk(user_id, project_id),
            "SK": workspace_sk(new_id),
            "id": new_id,
            "userId": user_id,
            "projectId": project_id,
            "name": f"{source.name[:248]} (copy)",
            "description": source.description,
            "locked": False,
            "sortOrder": max_order + 1,
            "settings": source.settings.model_dump(),
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        if source.content:
            item["content"] = source.content
        await self._put(item)
        return Workspace.model_validate(item)

    async def reorder(self, user_id: str, project_id: str, ordered_ids: list[str]) -> None:
        pk = workspace_pk(user_id, project_id)

        def _reorder() -> None:
            now = datetime.now(UTC)
            for index, ws_id in enumerate(ordered_ids, start=1):
                self._table.update_item(
                    Key={"PK": pk, "SK": workspace_sk(ws_id)},
                    UpdateExpression="SET #sortOrder = :sortOrder, #updatedAt = :updatedAt",
                    ExpressionAttributeNames={
                        "#sortOrder": "sortOrder",
                        "#updatedAt": "updatedAt",
                    },
                    ExpressionAttributeValues={
                        ":sortOrder": index,
                        ":updatedAt": now.isoformat(),
                    },
                    ConditionExpression="attribute_exists(PK)",
                )

        await asyncio.to_thread(_reorder)

    async def set_run(self, user_id: str, project_id: str, workspace_id: str, run: WorkspaceRun) -> None:
        """Update the latest run state on the workspace."""
        await self._update(
            workspace_pk(user_id, project_id),
            workspace_sk(workspace_id),
            {"run": run.model_dump(mode="json")},
        )
