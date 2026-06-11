"""Role vocabulary shared across the markdown codec's parse and emit steps."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from openfactcheck.prompts.variables import Role

ROLES: Final[tuple[Role, ...]] = ("system", "user", "assistant")
"""Role tags the markdown codec recognizes as block delimiters."""

ROLE_H1: Final[dict[Role, str]] = {
    "system": "# System Prompt",
    "user": "# User Prompt",
    "assistant": "# Assistant Prompt",
}
"""Required H1 heading for each role block, matched byte-for-byte after left-strip."""
