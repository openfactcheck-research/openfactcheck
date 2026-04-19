"""Shared helpers for DynamoDB repository implementations."""

from datetime import UTC, datetime
from typing import NamedTuple

from openfactcheck.api.repositories.dynamodb.types import AttrNames, AttrValues, DynamoItem


class UpdateExpression(NamedTuple):
    """DynamoDB SET update expression with attribute name/value mappings."""

    expression: str
    """The SET clause, e.g. ``"SET #name = :name, #age = :age"``."""

    attr_names: AttrNames
    """Mapping of ``#alias`` to field name for ``ExpressionAttributeNames``."""

    attr_values: AttrValues
    """Mapping of ``:placeholder`` to value for ``ExpressionAttributeValues``."""


def build_update_expression(
    values: DynamoItem,
    timestamp_field: str = "updatedAt",
) -> UpdateExpression:
    """Build a DynamoDB SET update expression from a values dict.

    Automatically sets a timestamp field to the current UTC time.

    Args:
        values: Field-to-value mapping to be SET on the item.
        timestamp_field: Name of the field that receives the auto-generated timestamp.
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
