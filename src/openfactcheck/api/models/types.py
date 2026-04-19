"""Shared type aliases for API models."""

from __future__ import annotations

type JSONString = str
"""A JSON-encoded string awaiting parse (e.g., a DynamoDB column containing serialized JSON)."""

type JSONScalar = str | int | float | bool | None
"""A JSON primitive: the set of values that live at the leaves of a JSON tree."""

type JSONValue = JSONScalar | dict[str, JSONValue] | list[JSONValue]
"""Any valid JSON value: a scalar, an object, or an array."""

type JSONObject = dict[str, JSONValue]
"""A JSON object: the top-level map of a decoded JSON document."""
