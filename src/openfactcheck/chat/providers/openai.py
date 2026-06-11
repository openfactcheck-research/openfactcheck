"""OpenAI provider definition.

Declares the OpenAI provider's capability flags and validates that a
[`ModelConfig`][ModelConfig] passed to [`ChatClient`][ChatClient] is an
[`OpenAIConfig`][OpenAIConfig].
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.config import OpenAIConfig
from openfactcheck.chat.errors import ProviderError
from openfactcheck.chat.providers.base import BaseProvider, ProviderCapabilities

if TYPE_CHECKING:
    from openfactcheck.chat.config import ModelConfig


class OpenAIProvider(BaseProvider):
    """OpenAI provider definition.

    Declares streaming, tool calling, and structured output as supported.
    """

    name = "openai"
    capabilities = ProviderCapabilities(
        streaming=True,
        tool_calling=True,
        structured_output=True,
    )

    def validate_config(self, config: ModelConfig) -> None:
        """Check that ``config`` is an [`OpenAIConfig`][OpenAIConfig].

        Args:
            config: Configuration to validate.

        Raises:
            ProviderError: If ``config`` is not an
                [`OpenAIConfig`][OpenAIConfig].
        """
        if not isinstance(config, OpenAIConfig):
            raise ProviderError(f"Expected OpenAIConfig, got {type(config).__name__}.")
