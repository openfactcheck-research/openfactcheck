"""Default backend dispatch for the chat layer.

Maps a provider name to its direct-SDK [`ChatBackend`][ChatBackend].
[`ChatClient`][ChatClient] consults this mapping when a caller does not
pass ``backend=`` explicitly.

Callers who want a non-default backend pass the backend instance to
[`ChatClient`][ChatClient] themselves.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.backends.anthropic import AnthropicBackend
from openfactcheck.chat.backends.openai import OpenAIBackend
from openfactcheck.chat.backends.openrouter import OpenRouterBackend
from openfactcheck.chat.errors import ProviderNotFoundError

if TYPE_CHECKING:
    from openfactcheck.chat.backends.base import ChatBackend
    from openfactcheck.chat.config import ProviderName


def default_backend(provider: ProviderName) -> ChatBackend:
    """Return the default direct-SDK backend for ``provider``.

    Args:
        provider: Provider identifier from
            [`ProviderName`][ProviderName].

    Returns:
        The direct-SDK [`ChatBackend`][ChatBackend] registered for
        ``provider``.

    Raises:
        ProviderNotFoundError: If no default backend is registered for
            ``provider``.
    """
    if provider == "openai":
        return OpenAIBackend()
    if provider == "anthropic":
        return AnthropicBackend()
    if provider == "openrouter":
        return OpenRouterBackend()
    raise ProviderNotFoundError(f"No default backend for provider {provider!r}.")
