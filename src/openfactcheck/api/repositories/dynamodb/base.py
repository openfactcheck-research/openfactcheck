# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Generic DynamoDB repository base — models own their keys, base handles CRUD."""

from __future__ import annotations

import asyncio
from typing import Any

from openfactcheck.api.repositories.dynamodb.client import get_table
from openfactcheck.api.repositories.dynamodb.helpers import build_update_expression


class BaseDynamoRepository:
    """Generic single-table DynamoDB operations.

    Entity repos extend this and add type-specific methods.
    """

    def __init__(self, table_name: str, region_name: str = "us-east-1") -> None:
        self._table = get_table(table_name, region_name)

    # -------------------------------------------------------------------------
    # Core operations
    # -------------------------------------------------------------------------

    async def _put(self, item: dict[str, Any]) -> None:
        """Write an item to the table."""
        await asyncio.to_thread(self._table.put_item, Item=item)

    async def _get(self, pk: str, sk: str) -> dict[str, Any] | None:
        """Get a single item by PK + SK."""

        def _do() -> dict[str, Any] | None:
            response = self._table.get_item(Key={"PK": pk, "SK": sk})
            return response.get("Item")

        return await asyncio.to_thread(_do)

    async def _update(self, pk: str, sk: str, values: dict[str, Any]) -> dict[str, Any] | None:
        """Update an item. Returns updated attributes or None if not found."""
        update_expr, attr_names, attr_values = build_update_expression(values)

        def _do() -> dict[str, Any] | None:
            try:
                response: dict[str, Any] = self._table.update_item(
                    Key={"PK": pk, "SK": sk},
                    UpdateExpression=update_expr,
                    ExpressionAttributeNames=attr_names,
                    ExpressionAttributeValues=attr_values,
                    ConditionExpression="attribute_exists(PK)",
                    ReturnValues="ALL_NEW",
                )
            except self._table.meta.client.exceptions.ConditionalCheckFailedException:
                return None
            return response["Attributes"]

        return await asyncio.to_thread(_do)

    async def _delete(self, pk: str, sk: str) -> bool:
        """Delete an item. Returns True if deleted, False if not found."""

        def _do() -> bool:
            try:
                self._table.delete_item(
                    Key={"PK": pk, "SK": sk},
                    ConditionExpression="attribute_exists(PK)",
                )
            except self._table.meta.client.exceptions.ConditionalCheckFailedException:
                return False
            return True

        return await asyncio.to_thread(_do)

    # -------------------------------------------------------------------------
    # Query operations
    # -------------------------------------------------------------------------

    async def _query_by_pk(
        self,
        pk: str,
        sk_prefix: str | None = None,
        projection: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query base table by PK, optionally filtering SK by prefix."""

        def _do() -> list[dict[str, Any]]:
            kwargs: dict[str, Any] = {
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": pk},
            }
            if sk_prefix:
                kwargs["KeyConditionExpression"] += " AND begins_with(SK, :prefix)"
                kwargs["ExpressionAttributeValues"][":prefix"] = sk_prefix
            if projection:
                kwargs["ProjectionExpression"] = projection

            response = self._table.query(**kwargs)
            return response.get("Items", [])

        return await asyncio.to_thread(_do)

    async def _query_gsi(self, index_name: str, key_name: str, key_value: str) -> list[dict[str, Any]]:
        """Query a GSI by its partition key."""

        def _do() -> list[dict[str, Any]]:
            response = self._table.query(
                IndexName=index_name,
                KeyConditionExpression=f"{key_name} = :val",
                ExpressionAttributeValues={":val": key_value},
            )
            return response.get("Items", [])

        return await asyncio.to_thread(_do)

    async def _batch_delete(self, items: list[dict[str, Any]]) -> None:
        """Batch delete items that have PK and SK attributes."""

        def _do() -> None:
            with self._table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        await asyncio.to_thread(_do)
