"""Shared helpers for DynamoDB repository implementations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_update_expression(
    values: dict[str, Any],
    timestamp_field: str = "updatedAt",
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Build a DynamoDB SET update expression from a values dict.

    Automatically appends an updatedAt timestamp.

    Returns:
        (update_expression, attr_names, attr_values)
    """
    update_parts: list[str] = []
    attr_names: dict[str, str] = {}
    attr_values: dict[str, Any] = {}

    for field, value in values.items():
        alias = f"#{field}"
        placeholder = f":{field}"
        update_parts.append(f"{alias} = {placeholder}")
        attr_names[alias] = field
        attr_values[placeholder] = value

    now = datetime.now(UTC)
    alias = f"#{timestamp_field}"
    placeholder = f":{timestamp_field}"
    update_parts.append(f"{alias} = {placeholder}")
    attr_names[alias] = timestamp_field
    attr_values[placeholder] = now.isoformat()

    return "SET " + ", ".join(update_parts), attr_names, attr_values
