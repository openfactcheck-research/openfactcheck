"""Tests for Anthropic backend param mapping."""

import pytest

from openfactcheck.chat.backends.anthropic.params import config_to_kwargs, response_format_kwargs
from openfactcheck.chat.config import AnthropicConfig, OpenAIConfig
from openfactcheck.chat.errors import ProviderError, UnsupportedFeatureError
from openfactcheck.chat.requests import ResponseFormat


def test_config_to_kwargs_minimal() -> None:
    """Minimal Anthropic config produces model + max_tokens kwargs."""
    config = AnthropicConfig(model="claude-sonnet-4-6", max_output_tokens=100)

    kwargs = config_to_kwargs(config)

    assert kwargs == {"model": "claude-sonnet-4-6", "max_tokens": 100}


def test_config_to_kwargs_all_fields() -> None:
    """All Anthropic-specific fields are forwarded."""
    config = AnthropicConfig(
        model="claude-sonnet-4-6",
        temperature=0.3,
        max_output_tokens=200,
        top_p=0.9,
        top_k=40,
        thinking=True,
        thinking_budget_tokens=1024,
    )

    kwargs = config_to_kwargs(config)

    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["temperature"] == 0.3
    assert kwargs["max_tokens"] == 200
    assert kwargs["top_p"] == 0.9
    assert kwargs["top_k"] == 40
    assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 1024}


def test_config_to_kwargs_missing_max_output_tokens_raises() -> None:
    """Anthropic requires max_output_tokens; backend prep raises ProviderError if absent."""
    config = AnthropicConfig(model="claude-sonnet-4-6")

    with pytest.raises(ProviderError, match="max_output_tokens"):
        config_to_kwargs(config)


def test_config_to_kwargs_rejects_openai() -> None:
    """Direct Anthropic backend refuses non-Anthropic configs."""
    config = OpenAIConfig(model="gpt-4o")

    with pytest.raises(UnsupportedFeatureError, match="does not support provider 'openai'"):
        config_to_kwargs(config)


def test_response_format_kwargs_uses_forced_tool() -> None:
    """Structured output becomes a single forced tool whose input_schema is the model schema."""
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    response_format = ResponseFormat(name="Person", json_schema=schema)

    kwargs = response_format_kwargs(response_format)

    assert kwargs["tools"] == [{"name": "Person", "input_schema": schema}]
    assert kwargs["tool_choice"] == {"type": "tool", "name": "Person"}
