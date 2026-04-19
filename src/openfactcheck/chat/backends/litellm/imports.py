"""Lazy import of the ``litellm`` module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.errors import ProviderNotFoundError

if TYPE_CHECKING:
    from types import ModuleType


def load_litellm() -> ModuleType:
    """Lazily import and return the ``litellm`` module.

    Raises:
        ProviderNotFoundError: If litellm is not installed.
    """
    try:
        import litellm
    except ImportError:
        raise ProviderNotFoundError(
            "litellm backend requires litellm. Install with: pip install openfactcheck[litellm]"
        ) from None
    return litellm
