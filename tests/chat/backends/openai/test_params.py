"""Tests for OpenAI backend param mapping."""

import pytest

from openfactcheck.chat.backends.openai.params import config_to_kwargs
from openfactcheck.chat.config import AnthropicConfig, OpenAIConfig
from openfactcheck.chat.errors import UnsupportedFeatureError


def test_config_to_kwargs_minimal() -> None:
    """Minimal OpenAI config produces model-only kwargs (no runtime fields)."""
    config = OpenAIConfig(model="gpt-4o")

    kwargs = config_to_kwargs(config)

    assert kwargs == {"model": "gpt-4o"}


def test_config_to_kwargs_all_fields() -> None:
    """All OpenAI-specific fields are forwarded."""
    config = OpenAIConfig(
        model="gpt-4o",
        temperature=0.3,
        max_output_tokens=100,
        top_p=0.9,
        seed=42,
        frequency_penalty=0.5,
        presence_penalty=0.2,
        reasoning_effort="medium",
    )

    kwargs = config_to_kwargs(config)

    assert kwargs["model"] == "gpt-4o"
    assert kwargs["temperature"] == 0.3
    assert kwargs["max_tokens"] == 100
    assert kwargs["top_p"] == 0.9
    assert kwargs["seed"] == 42
    assert kwargs["frequency_penalty"] == 0.5
    assert kwargs["presence_penalty"] == 0.2
    assert kwargs["reasoning_effort"] == "medium"


def test_config_to_kwargs_rejects_anthropic() -> None:
    """Direct OpenAI backend refuses non-OpenAI configs."""
    config = AnthropicConfig(model="claude-sonnet-4-6")

    with pytest.raises(UnsupportedFeatureError, match="does not support provider 'anthropic'"):
        config_to_kwargs(config)
