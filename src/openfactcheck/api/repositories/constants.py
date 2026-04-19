"""Shared constants and utilities for repository implementations."""

from secrets import token_urlsafe

MAX_PROJECTS_PER_USER = 50
"""Upper limit on the number of projects a single user may own."""

MAX_WORKSPACES_PER_PROJECT = 5
"""Upper limit on the number of workspaces a single project may contain."""

MAX_CONTENT_BYTES = 350_000
"""Upper limit on the serialized size of a workspace's content blob."""

MAX_PIPELINE_BYTES = 500_000
"""Upper limit on the serialized size of a compiled pipeline."""


def generate_id() -> str:
    """Generate a URL-safe 12-character identifier."""
    return token_urlsafe(9)  # 9 bytes → 12 base64 chars
