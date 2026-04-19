"""Provider lookup for the chat layer.

Each supported chat provider has a concrete [`BaseProvider`][BaseProvider]
subclass. [`get_provider`][get_provider] returns the matching provider
for a given ``config.provider`` name.

End users rarely call [`get_provider`][get_provider] directly;
[`ChatClient`][ChatClient] uses it internally to dispatch on
``config.provider``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.errors import ProviderNotFoundError
from openfactcheck.chat.providers.anthropic import AnthropicProvider
from openfactcheck.chat.providers.openai import OpenAIProvider

if TYPE_CHECKING:
    from openfactcheck.chat.providers.base import BaseProvider

_PROVIDERS: dict[str, BaseProvider] = {
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
}


def get_provider(name: str) -> BaseProvider:
    """Return the provider definition matching ``name``.

    Args:
        name: Provider identifier from ``config.provider``.

    Returns:
        The provider definition for ``name``.

    Raises:
        ProviderNotFoundError: If ``name`` is not a known provider.
    """
    provider = _PROVIDERS.get(name)
    if provider is None:
        supported = ", ".join(sorted(_PROVIDERS))
        raise ProviderNotFoundError(f"Unknown provider '{name}'. Supported: {supported}.")
    return provider
