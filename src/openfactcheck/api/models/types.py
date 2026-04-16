"""Shared type aliases for API models."""

from __future__ import annotations

type JSONString = str
type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | dict[str, JSONValue] | list[JSONValue]
type JSONObject = dict[str, JSONValue]
