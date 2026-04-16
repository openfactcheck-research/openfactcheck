"""Shared type aliases for DynamoDB repositories."""

from typing import Any

type DynamoItem = dict[str, Any]
type AttrNames = dict[str, str]
type AttrValues = dict[str, Any]
