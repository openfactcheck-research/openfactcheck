"""Generic DynamoDB repository base for single-table entities."""

import asyncio

from openfactcheck.api.repositories.dynamodb.client import get_table
from openfactcheck.api.repositories.dynamodb.helpers import build_update_expression
from openfactcheck.api.repositories.dynamodb.types import DynamoItem


class BaseDynamoRepository:
    """Generic single-table DynamoDB operations.

    Entity repos extend this and add type-specific methods.
    """

    def __init__(self, table_name: str, region_name: str = "us-east-1") -> None:
        """Build a repository bound to a specific DynamoDB table.

        Args:
            table_name: Name of the DynamoDB table.
            region_name: AWS region where the table lives.
        """
        self._table = get_table(table_name, region_name)

    async def _put(self, item: DynamoItem) -> None:
        """Write an item to the table."""

        def _do() -> None:
            self._table.put_item(Item=item)

        await asyncio.to_thread(_do)

    async def _get(self, pk: str, sk: str) -> DynamoItem | None:
        """Get a single item by PK + SK."""

        def _do() -> DynamoItem | None:
            response = self._table.get_item(Key={"PK": pk, "SK": sk})
            return response.get("Item")

        return await asyncio.to_thread(_do)

    async def _update(self, pk: str, sk: str, values: DynamoItem) -> DynamoItem | None:
        """Update an item. Returns updated attributes or None if not found."""
        update = build_update_expression(values)

        def _do() -> DynamoItem | None:
            try:
                response = self._table.update_item(
                    Key={"PK": pk, "SK": sk},
                    UpdateExpression=update.expression,
                    ExpressionAttributeNames=update.attr_names,
                    ExpressionAttributeValues=update.attr_values,
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

    async def _query_by_pk(
        self,
        pk: str,
        sk_prefix: str | None = None,
        projection: str | None = None,
    ) -> list[DynamoItem]:
        """Query base table by PK, optionally filtering SK by prefix."""

        def _do() -> list[DynamoItem]:
            kwargs: DynamoItem = {
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

    async def _query_gsi(self, index_name: str, key_name: str, key_value: str) -> list[DynamoItem]:
        """Query a GSI by its partition key."""

        def _do() -> list[DynamoItem]:
            response = self._table.query(
                IndexName=index_name,
                KeyConditionExpression=f"{key_name} = :val",
                ExpressionAttributeValues={":val": key_value},
            )
            return response.get("Items", [])

        return await asyncio.to_thread(_do)

    async def _batch_delete(self, items: list[DynamoItem]) -> None:
        """Batch delete items that have PK and SK attributes."""

        def _do() -> None:
            with self._table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

        await asyncio.to_thread(_do)
