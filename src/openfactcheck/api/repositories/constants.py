"""Shared constants and utilities for all repository implementations."""

from __future__ import annotations

from secrets import token_urlsafe

MAX_PROJECTS_PER_USER = 50
MAX_WORKSPACES_PER_PROJECT = 5


def generate_id() -> str:
    """Generate a URL-safe 12-character ID."""
    return token_urlsafe(9)  # 9 bytes → 12 base64 chars
