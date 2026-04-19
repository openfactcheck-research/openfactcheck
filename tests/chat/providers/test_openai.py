"""Tests for OpenAI provider validation."""

import pytest

from openfactcheck.chat.config import AnthropicConfig, OpenAIConfig
from openfactcheck.chat.errors import ProviderError
from openfactcheck.chat.providers.openai import OpenAIProvider


@pytest.fixture()
def provider() -> OpenAIProvider:
    """OpenAI provider instance."""
    return OpenAIProvider()


def test_OpenAIProvider_validate_config_valid(provider: OpenAIProvider) -> None:
    """Valid OpenAIConfig passes validation."""
    config = OpenAIConfig(model="gpt-4o", temperature=0.5)

    provider.validate_config(config)  # should not raise.


def test_OpenAIProvider_validate_config_wrong_type(provider: OpenAIProvider) -> None:
    """AnthropicConfig passed to OpenAIProvider raises ProviderError."""
    config = AnthropicConfig(model="claude-sonnet-4-6")

    with pytest.raises(ProviderError, match="Expected OpenAIConfig"):
        provider.validate_config(config)


def test_OpenAIProvider_capabilities(provider: OpenAIProvider) -> None:
    """OpenAI provider declares expected capabilities."""
    assert provider.capabilities.streaming is True
    assert provider.capabilities.tool_calling is True
    assert provider.capabilities.structured_output is True
