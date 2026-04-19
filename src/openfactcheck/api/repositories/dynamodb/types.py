"""Shared type aliases for DynamoDB repositories."""

from typing import Any

type DynamoItem = dict[str, Any]
"""A single DynamoDB record: attribute names mapped to their stored values."""

type AttrNames = dict[str, str]
"""Expression attribute names: ``#alias`` placeholders mapped to real attribute names."""

type AttrValues = dict[str, Any]
"""Expression attribute values: ``:placeholder`` tokens mapped to their bound values."""
