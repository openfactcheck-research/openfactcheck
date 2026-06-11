"""Tests for OpenRouter provider validation."""

import pytest

from openfactcheck.chat.config import OpenAIConfig, OpenRouterConfig
from openfactcheck.chat.errors import ProviderError
from openfactcheck.chat.providers.openrouter import OpenRouterProvider


@pytest.fixture()
def provider() -> OpenRouterProvider:
    """OpenRouter provider instance."""
    return OpenRouterProvider()


def test_OpenRouterProvider_validate_config_valid(provider: OpenRouterProvider) -> None:
    """Valid OpenRouterConfig passes validation."""
    config = OpenRouterConfig(model="openai/gpt-4o", temperature=0.5)

    provider.validate_config(config)  # should not raise.


def test_OpenRouterProvider_validate_config_wrong_type(provider: OpenRouterProvider) -> None:
    """OpenAIConfig passed to OpenRouterProvider raises ProviderError."""
    config = OpenAIConfig(model="gpt-4o")

    with pytest.raises(ProviderError, match="Expected OpenRouterConfig"):
        provider.validate_config(config)


def test_OpenRouterProvider_capabilities(provider: OpenRouterProvider) -> None:
    """OpenRouter provider declares expected capabilities."""
    assert provider.capabilities.streaming is True
    assert provider.capabilities.tool_calling is True
    assert provider.capabilities.structured_output is True
