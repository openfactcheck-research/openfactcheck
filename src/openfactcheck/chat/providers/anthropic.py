"""Anthropic provider definition.

Declares the Anthropic provider's capability flags and validates that a
[`ModelConfig`][ModelConfig] passed to [`ChatClient`][ChatClient] is an
[`AnthropicConfig`][AnthropicConfig] with the provider-required fields set.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactcheck.chat.config import AnthropicConfig
from openfactcheck.chat.errors import ProviderError
from openfactcheck.chat.providers.base import BaseProvider, ProviderCapabilities

if TYPE_CHECKING:
    from openfactcheck.chat.config import ModelConfig


class AnthropicProvider(BaseProvider):
    """Anthropic provider definition.

    Declares streaming, tool calling, and structured output as supported.
    Requires ``max_output_tokens`` to be set on the config, since
    Anthropic's API rejects requests without an explicit output cap.
    """

    name = "anthropic"
    capabilities = ProviderCapabilities(
        streaming=True,
        tool_calling=True,
        structured_output=True,
    )

    def validate_config(self, config: ModelConfig) -> None:
        """Check that ``config`` is an [`AnthropicConfig`][AnthropicConfig] with required fields.

        Args:
            config: Configuration to validate.

        Raises:
            ProviderError: If ``config`` is not an
                [`AnthropicConfig`][AnthropicConfig], or if
                ``max_output_tokens`` is not set.
        """
        if not isinstance(config, AnthropicConfig):
            raise ProviderError(f"Expected AnthropicConfig, got {type(config).__name__}.")
        if config.max_output_tokens is None:
            raise ProviderError("Anthropic requires max_output_tokens; set it on AnthropicConfig.")
