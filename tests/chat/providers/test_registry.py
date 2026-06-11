"""Tests for provider registry."""

import pytest

from openfactcheck.chat.errors import ProviderNotFoundError
from openfactcheck.chat.providers import get_provider
from openfactcheck.chat.providers.anthropic import AnthropicProvider
from openfactcheck.chat.providers.openai import OpenAIProvider
from openfactcheck.chat.providers.openrouter import OpenRouterProvider


def test_get_provider_openai() -> None:
    """Registry returns OpenAIProvider for 'openai'."""
    provider = get_provider("openai")

    assert isinstance(provider, OpenAIProvider)
    assert provider.name == "openai"


def test_get_provider_openrouter() -> None:
    """Registry returns OpenRouterProvider for 'openrouter'."""
    provider = get_provider("openrouter")

    assert isinstance(provider, OpenRouterProvider)
    assert provider.name == "openrouter"


def test_get_provider_anthropic() -> None:
    """Registry returns AnthropicProvider for 'anthropic'."""
    provider = get_provider("anthropic")

    assert isinstance(provider, AnthropicProvider)
    assert provider.name == "anthropic"


def test_get_provider_unknown() -> None:
    """Unknown provider raises ProviderNotFoundError."""
    with pytest.raises(ProviderNotFoundError, match="Unknown provider 'fake'"):
        get_provider("fake")
