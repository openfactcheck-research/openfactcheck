"""Lazy import of the ``anthropic`` SDK clients."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.errors import ProviderNotFoundError

if TYPE_CHECKING:
    from anthropic import Anthropic, AsyncAnthropic


def load_anthropic() -> type[Anthropic]:
    """Lazily import and return the ``Anthropic`` sync client class."""
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ProviderNotFoundError(
            "Anthropic backend requires the anthropic SDK. Install with: pip install openfactcheck[anthropic]"
        ) from None
    return Anthropic


def load_async_anthropic() -> type[AsyncAnthropic]:
    """Lazily import and return the ``AsyncAnthropic`` async client class."""
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        raise ProviderNotFoundError(
            "Anthropic backend requires the anthropic SDK. Install with: pip install openfactcheck[anthropic]"
        ) from None
    return AsyncAnthropic
