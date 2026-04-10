# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""DynamoDB implementation of the workspace repository."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from openfactcheck.api.models import Workspace, WorkspaceCreate, WorkspaceSettings, WorkspaceUpdate
from openfactcheck.api.repositories.constants import MAX_WORKSPACES_PER_PROJECT, generate_id
from openfactcheck.api.repositories.dynamodb.client import get_table
from openfactcheck.api.repositories.dynamodb.keys import workspace_gs1pk, workspace_pk


def _item_to_model(item: dict[str, Any]) -> Workspace:
    settings_raw = item.get("settings", "{}")
    settings_str = settings_raw if isinstance(settings_raw, str) else json.dumps(settings_raw)

    return Workspace(
        id=item["id"],
        user_id=item["userId"],
        project_id=item["projectId"],
        name=item["name"],
        description=item.get("description", ""),
        locked=item.get("locked", False),
        sort_order=int(item.get("sortOrder", 0)),
        settings=WorkspaceSettings.model_validate_json(settings_str),
        content=item.get("content"),
        created_at=datetime.fromisoformat(item["createdAt"]),
        updated_at=datetime.fromisoformat(item["updatedAt"]),
    )


class DynamoWorkspaceRepository:
    """Workspace CRUD backed by DynamoDB single-table design."""

    def __init__(self, table_name: str, region_name: str = "us-east-1") -> None:
        self._table = get_table(table_name, region_name)

    def _list_items_sync(self, user_id: str, project_id: str) -> list[dict[str, Any]]:
        response = self._table.query(
            IndexName="gs1",
            KeyConditionExpression="GS1PK = :gs1pk",
            FilterExpression="begins_with(PK, :prefix)",
            ExpressionAttributeValues={
                ":gs1pk": workspace_gs1pk(user_id, project_id),
                ":prefix": f"USER#{user_id}#PROJECT#{project_id}#WORKSPACE#",
            },
        )
        return response.get("Items", [])

    async def list_by_project(self, user_id: str, project_id: str) -> list[Workspace]:
        items = await asyncio.to_thread(self._list_items_sync, user_id, project_id)
        workspaces = [_item_to_model(item) for item in items]
        return sorted(workspaces, key=lambda w: w.sort_order)

    async def get(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None:
        def _get() -> Workspace | None:
            response = self._table.get_item(
                Key={"PK": workspace_pk(user_id, project_id, workspace_id)},
            )
            item: dict[str, Any] | None = response.get("Item")
            return _item_to_model(item) if item else None

        return await asyncio.to_thread(_get)

    async def create(self, user_id: str, project_id: str, data: WorkspaceCreate) -> Workspace | None:
        def _create() -> Workspace | None:
            items = self._list_items_sync(user_id, project_id)
            if len(items) >= MAX_WORKSPACES_PER_PROJECT:
                return None

            max_order = max((int(i.get("sortOrder", 0)) for i in items), default=0)

            now = datetime.now(UTC)
            workspace_id = generate_id()
            item: dict[str, Any] = {
                "PK": workspace_pk(user_id, project_id, workspace_id),
                "GS1PK": workspace_gs1pk(user_id, project_id),
                "id": workspace_id,
                "userId": user_id,
                "projectId": project_id,
                "name": data.name,
                "description": data.description,
                "locked": False,
                "sortOrder": max_order + 1,
                "settings": "{}",
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
            self._table.put_item(Item=item)
            return _item_to_model(item)

        return await asyncio.to_thread(_create)

    async def update(self, user_id: str, project_id: str, workspace_id: str, data: WorkspaceUpdate) -> Workspace | None:
        update_parts: list[str] = []
        attr_names: dict[str, str] = {}
        attr_values: dict[str, Any] = {}

        if data.name is not None:
            update_parts.append("#name = :name")
            attr_names["#name"] = "name"
            attr_values[":name"] = data.name
        if data.description is not None:
            update_parts.append("#description = :description")
            attr_names["#description"] = "description"
            attr_values[":description"] = data.description
        if data.locked is not None:
            update_parts.append("#locked = :locked")
            attr_names["#locked"] = "locked"
            attr_values[":locked"] = data.locked
        if data.settings is not None:
            update_parts.append("#settings = :settings")
            attr_names["#settings"] = "settings"
            attr_values[":settings"] = data.settings.model_dump_json()
        if data.content is not None:
            update_parts.append("#content = :content")
            attr_names["#content"] = "content"
            attr_values[":content"] = data.content

        if not update_parts:
            return await self.get(user_id, project_id, workspace_id)

        now = datetime.now(UTC)
        update_parts.append("#updatedAt = :updatedAt")
        attr_names["#updatedAt"] = "updatedAt"
        attr_values[":updatedAt"] = now.isoformat()

        pk = workspace_pk(user_id, project_id, workspace_id)

        def _update() -> dict[str, Any] | None:
            try:
                response: dict[str, Any] = self._table.update_item(
                    Key={"PK": pk},
                    UpdateExpression="SET " + ", ".join(update_parts),
                    ExpressionAttributeNames=attr_names,
                    ExpressionAttributeValues=attr_values,
                    ConditionExpression="attribute_exists(PK)",
                    ReturnValues="ALL_NEW",
                )
            except self._table.meta.client.exceptions.ConditionalCheckFailedException:
                return None
            return response["Attributes"]

        attrs = await asyncio.to_thread(_update)
        return _item_to_model(attrs) if attrs else None

    async def delete(self, user_id: str, project_id: str, workspace_id: str) -> bool:
        pk = workspace_pk(user_id, project_id, workspace_id)

        def _delete() -> bool:
            try:
                self._table.delete_item(
                    Key={"PK": pk},
                    ConditionExpression="attribute_exists(PK)",
                )
            except self._table.meta.client.exceptions.ConditionalCheckFailedException:
                return False
            return True

        return await asyncio.to_thread(_delete)

    async def duplicate(self, user_id: str, project_id: str, workspace_id: str) -> Workspace | None:
        source = await self.get(user_id, project_id, workspace_id)
        if source is None:
            return None

        def _duplicate() -> Workspace | None:
            items = self._list_items_sync(user_id, project_id)
            if len(items) >= MAX_WORKSPACES_PER_PROJECT:
                return None

            max_order = max((int(i.get("sortOrder", 0)) for i in items), default=0)

            now = datetime.now(UTC)
            new_id = generate_id()
            item: dict[str, Any] = {
                "PK": workspace_pk(user_id, project_id, new_id),
                "GS1PK": workspace_gs1pk(user_id, project_id),
                "id": new_id,
                "userId": user_id,
                "projectId": project_id,
                "name": f"{source.name[:248]} (copy)",
                "description": source.description,
                "locked": False,
                "sortOrder": max_order + 1,
                "settings": json.dumps(source.settings.model_dump()),
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
            if source.content:
                item["content"] = source.content
            self._table.put_item(Item=item)
            return _item_to_model(item)

        return await asyncio.to_thread(_duplicate)

    async def reorder(self, user_id: str, project_id: str, ordered_ids: list[str]) -> None:
        now = datetime.now(UTC)

        def _reorder() -> None:
            for index, ws_id in enumerate(ordered_ids, start=1):
                pk = workspace_pk(user_id, project_id, ws_id)
                self._table.update_item(
                    Key={"PK": pk},
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
