"""Tests for litellm param mapping."""

from openfactcheck.chat.backends.litellm.params import config_to_kwargs
from openfactcheck.chat.config import AnthropicConfig, OpenAIConfig, RuntimeConfig


def test_config_to_kwargs_openai_minimal() -> None:
    """Minimal OpenAI config produces model string and default retries."""
    config = OpenAIConfig(model="gpt-4o")
    runtime = RuntimeConfig()

    kwargs = config_to_kwargs(config, runtime)

    assert kwargs["model"] == "openai/gpt-4o"
    assert kwargs["num_retries"] == 2
    assert "temperature" not in kwargs


def test_config_to_kwargs_openai_full() -> None:
    """OpenAI-specific fields are forwarded."""
    config = OpenAIConfig(
        model="gpt-4o",
        temperature=0.3,
        max_output_tokens=100,
        seed=42,
        frequency_penalty=0.5,
        reasoning_effort="medium",
    )
    runtime = RuntimeConfig(timeout=30.0, max_retries=5)

    kwargs = config_to_kwargs(config, runtime)

    assert kwargs["model"] == "openai/gpt-4o"
    assert kwargs["temperature"] == 0.3
    assert kwargs["max_tokens"] == 100
    assert kwargs["seed"] == 42
    assert kwargs["frequency_penalty"] == 0.5
    assert kwargs["reasoning_effort"] == "medium"
    assert kwargs["timeout"] == 30.0
    assert kwargs["num_retries"] == 5


def test_config_to_kwargs_anthropic_thinking() -> None:
    """Anthropic thinking config becomes a dict."""
    config = AnthropicConfig(
        model="claude-sonnet-4-6",
        top_k=40,
        thinking=True,
        thinking_budget_tokens=10_000,
    )
    runtime = RuntimeConfig()

    kwargs = config_to_kwargs(config, runtime)

    assert kwargs["model"] == "anthropic/claude-sonnet-4-6"
    assert kwargs["top_k"] == 40
    assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 10_000}
