"""OpenRouter provider definition.

Declares the OpenRouter provider's capability flags and validates that a
[`ModelConfig`][ModelConfig] passed to [`ChatClient`][ChatClient] is an
[`OpenRouterConfig`][OpenRouterConfig].
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.config import OpenRouterConfig
from openfactcheck.chat.errors import ProviderError
from openfactcheck.chat.providers.base import BaseProvider, ProviderCapabilities

if TYPE_CHECKING:
    from openfactcheck.chat.config import ModelConfig


class OpenRouterProvider(BaseProvider):
    """OpenRouter provider definition.

    Declares streaming, tool calling, and structured output as supported;
    actual per-model support depends on the upstream model OpenRouter routes
    to.
    """

    name = "openrouter"
    capabilities = ProviderCapabilities(
        streaming=True,
        tool_calling=True,
        structured_output=True,
    )

    def validate_config(self, config: ModelConfig) -> None:
        """Check that ``config`` is an [`OpenRouterConfig`][OpenRouterConfig].

        Args:
            config: Configuration to validate.

        Raises:
            ProviderError: If ``config`` is not an
                [`OpenRouterConfig`][OpenRouterConfig].
        """
        if not isinstance(config, OpenRouterConfig):
            raise ProviderError(f"Expected OpenRouterConfig, got {type(config).__name__}.")
