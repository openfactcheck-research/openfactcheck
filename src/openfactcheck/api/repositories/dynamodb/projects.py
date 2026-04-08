# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""DynamoDB implementation of the project repository."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from openfactcheck.api.models import Project, ProjectCreate, ProjectUpdate
from openfactcheck.api.repositories.constants import MAX_PROJECTS_PER_USER, generate_id
from openfactcheck.api.repositories.dynamodb.client import get_table
from openfactcheck.api.repositories.dynamodb.keys import project_gs1pk, project_pk


def _item_to_model(item: dict[str, Any]) -> Project:
    return Project(
        id=item["id"],
        user_id=item["userId"],
        name=item["name"],
        created_at=datetime.fromisoformat(item["createdAt"]),
        updated_at=datetime.fromisoformat(item["updatedAt"]),
    )


class DynamoProjectRepository:
    """Project CRUD backed by DynamoDB single-table design."""

    def __init__(self, table_name: str, region_name: str = "us-east-1") -> None:
        self._table = get_table(table_name, region_name)

    async def list_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> list[Project]:
        def _query() -> list[Project]:
            response = self._table.query(
                IndexName="gs1",
                KeyConditionExpression="GS1PK = :gs1pk",
                FilterExpression="begins_with(PK, :prefix)",
                ExpressionAttributeValues={
                    ":gs1pk": project_gs1pk(user_id),
                    ":prefix": f"USER#{user_id}#PROJECT#",
                },
            )
            items: list[dict[str, Any]] = response.get("Items", [])
            projects = sorted((_item_to_model(item) for item in items), key=lambda p: p.created_at)
            return projects[offset : offset + limit]

        return await asyncio.to_thread(_query)

    async def get(self, user_id: str, project_id: str) -> Project | None:
        def _get() -> Project | None:
            response = self._table.get_item(
                Key={"PK": project_pk(user_id, project_id)},
            )
            item: dict[str, Any] | None = response.get("Item")
            return _item_to_model(item) if item else None

        return await asyncio.to_thread(_get)

    async def create(self, user_id: str, data: ProjectCreate) -> Project | None:
        existing = await self.list_by_user(user_id)
        if len(existing) >= MAX_PROJECTS_PER_USER:
            return None

        now = datetime.now(UTC)
        project_id = generate_id()
        item: dict[str, Any] = {
            "PK": project_pk(user_id, project_id),
            "GS1PK": project_gs1pk(user_id),
            "id": project_id,
            "userId": user_id,
            "name": data.name,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }

        def _put() -> None:
            self._table.put_item(Item=item)

        await asyncio.to_thread(_put)
        return _item_to_model(item)

    async def update(self, user_id: str, project_id: str, data: ProjectUpdate) -> Project | None:
        values = data.model_dump(exclude_none=True)
        if not values:
            return await self.get(user_id, project_id)

        now = datetime.now(UTC)
        update_parts: list[str] = []
        attr_names: dict[str, str] = {}
        attr_values: dict[str, Any] = {}

        for field, value in values.items():
            alias = f"#{field}"
            placeholder = f":{field}"
            update_parts.append(f"{alias} = {placeholder}")
            attr_names[alias] = field
            attr_values[placeholder] = value

        update_parts.append("#updatedAt = :updatedAt")
        attr_names["#updatedAt"] = "updatedAt"
        attr_values[":updatedAt"] = now.isoformat()

        pk = project_pk(user_id, project_id)

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

    async def delete(self, user_id: str, project_id: str) -> bool:
        from openfactcheck.api.repositories.dynamodb.keys import workspace_gs1pk

        pk = project_pk(user_id, project_id)

        def _delete() -> bool:
            try:
                self._table.delete_item(
                    Key={"PK": pk},
                    ConditionExpression="attribute_exists(PK)",
                )
            except self._table.meta.client.exceptions.ConditionalCheckFailedException:
                return False

            # Cascade — delete all workspaces belonging to this project
            gs1pk = workspace_gs1pk(user_id, project_id)
            response = self._table.query(
                IndexName="gs1",
                KeyConditionExpression="GS1PK = :gs1pk",
                ExpressionAttributeValues={":gs1pk": gs1pk},
                ProjectionExpression="PK",
            )
            items: list[dict[str, Any]] = response.get("Items", [])
            with self._table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"PK": item["PK"]})

            return True

        return await asyncio.to_thread(_delete)
