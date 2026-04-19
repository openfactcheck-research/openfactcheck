"""Tests for Anthropic provider validation."""

import pytest

from openfactcheck.chat.config import AnthropicConfig, OpenAIConfig
from openfactcheck.chat.errors import ProviderError
from openfactcheck.chat.providers.anthropic import AnthropicProvider


@pytest.fixture()
def provider() -> AnthropicProvider:
    """Anthropic provider instance."""
    return AnthropicProvider()


def test_AnthropicProvider_validate_config_valid(provider: AnthropicProvider) -> None:
    """Valid AnthropicConfig passes validation."""
    config = AnthropicConfig(model="claude-sonnet-4-6", max_output_tokens=200)

    provider.validate_config(config)  # should not raise.


def test_AnthropicProvider_validate_config_wrong_type(provider: AnthropicProvider) -> None:
    """OpenAIConfig passed to AnthropicProvider raises ProviderError."""
    config = OpenAIConfig(model="gpt-4o")

    with pytest.raises(ProviderError, match="Expected AnthropicConfig"):
        provider.validate_config(config)


def test_AnthropicProvider_validate_config_requires_max_output_tokens(provider: AnthropicProvider) -> None:
    """AnthropicConfig without max_output_tokens is rejected at validation time."""
    config = AnthropicConfig(model="claude-sonnet-4-6")

    with pytest.raises(ProviderError, match="max_output_tokens"):
        provider.validate_config(config)


def test_AnthropicProvider_capabilities(provider: AnthropicProvider) -> None:
    """Anthropic provider declares expected capabilities."""
    assert provider.capabilities.streaming is True
    assert provider.capabilities.tool_calling is True
    assert provider.capabilities.structured_output is True
