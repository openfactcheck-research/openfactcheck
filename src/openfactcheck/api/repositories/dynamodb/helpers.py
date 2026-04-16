"""Shared helpers for DynamoDB repository implementations."""

from datetime import UTC, datetime
from typing import NamedTuple

from openfactcheck.api.repositories.dynamodb.types import AttrNames, AttrValues, DynamoItem


class UpdateExpression(NamedTuple):
    """DynamoDB SET update expression with attribute name/value mappings."""

    expression: str
    attr_names: AttrNames
    attr_values: AttrValues


def build_update_expression(
    values: DynamoItem,
    timestamp_field: str = "updatedAt",
) -> UpdateExpression:
    """Build a DynamoDB SET update expression from a values dict.

    Automatically appends an updatedAt timestamp.
    """
    update_parts: list[str] = []
    attr_names: AttrNames = {}
    attr_values: AttrValues = {}

    def _add(field: str, value: object) -> None:
        alias = f"#{field}"
        placeholder = f":{field}"
        update_parts.append(f"{alias} = {placeholder}")
        attr_names[alias] = field
        attr_values[placeholder] = value

    for field, value in values.items():
        _add(field, value)

    _add(timestamp_field, datetime.now(UTC).isoformat())

    return UpdateExpression("SET " + ", ".join(update_parts), attr_names, attr_values)
