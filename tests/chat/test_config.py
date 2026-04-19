"""Tests for LLM config types."""

import pytest
from pydantic import TypeAdapter, ValidationError

from openfactcheck.chat.config import (
    AnthropicConfig,
    BaseModelConfig,
    ModelConfig,
    OpenAIConfig,
    RuntimeConfig,
)


# ---------------------------------------------------------------------------
# BaseModelConfig
# ---------------------------------------------------------------------------


def test_BaseModelConfig_not_in_union() -> None:
    """BaseModelConfig has no provider field — cannot be parsed as ModelConfig."""
    adapter = TypeAdapter(ModelConfig)

    with pytest.raises(ValidationError):
        adapter.validate_python({"model": "gpt-4o"})


# ---------------------------------------------------------------------------
# OpenAIConfig
# ---------------------------------------------------------------------------


def test_OpenAIConfig_minimal() -> None:
    """OpenAIConfig with model only."""
    config = OpenAIConfig(model="gpt-4o")

    assert config.provider == "openai"
    assert config.model == "gpt-4o"
    assert config.temperature is None


def test_OpenAIConfig_with_params() -> None:
    """OpenAIConfig with provider-specific params."""
    config = OpenAIConfig(
        model="gpt-4o",
        temperature=0.5,
        max_output_tokens=100,
        seed=42,
        frequency_penalty=0.3,
    )

    assert config.temperature == 0.5
    assert config.max_output_tokens == 100
    assert config.seed == 42
    assert config.frequency_penalty == 0.3


def test_OpenAIConfig_temperature_out_of_range() -> None:
    """Temperature above 2.0 is rejected."""
    with pytest.raises(ValidationError):
        OpenAIConfig(model="gpt-4o", temperature=3.0)


def test_OpenAIConfig_frozen() -> None:
    """OpenAIConfig is immutable."""
    config = OpenAIConfig(model="gpt-4o")

    with pytest.raises(ValidationError):
        config.model = "other"  # type: ignore[misc] - frozen rejects mutation.


def test_OpenAIConfig_forbids_extra() -> None:
    """Extra fields are rejected."""
    with pytest.raises(ValidationError, match="extra"):
        OpenAIConfig(model="gpt-4o", unknown="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# AnthropicConfig
# ---------------------------------------------------------------------------


def test_AnthropicConfig_minimal() -> None:
    """AnthropicConfig with model only."""
    config = AnthropicConfig(model="claude-sonnet-4-6")

    assert config.provider == "anthropic"
    assert config.model == "claude-sonnet-4-6"


def test_AnthropicConfig_with_thinking() -> None:
    """AnthropicConfig with extended thinking enabled."""
    config = AnthropicConfig(
        model="claude-opus-4-6",
        thinking=True,
        thinking_budget_tokens=10000,
    )

    assert config.thinking is True
    assert config.thinking_budget_tokens == 10000


def test_AnthropicConfig_thinking_requires_budget() -> None:
    """thinking=True without a budget is rejected at construction."""
    with pytest.raises(ValidationError, match="thinking_budget_tokens is required"):
        AnthropicConfig(model="claude-opus-4-6", thinking=True)


def test_AnthropicConfig_budget_without_thinking_rejected() -> None:
    """thinking_budget_tokens without thinking=True is rejected."""
    with pytest.raises(ValidationError, match="must not be set when thinking=False"):
        AnthropicConfig(model="claude-opus-4-6", thinking_budget_tokens=1024)


def test_AnthropicConfig_top_k_must_be_positive() -> None:
    """top_k must be > 0."""
    with pytest.raises(ValidationError):
        AnthropicConfig(model="claude-sonnet-4-6", top_k=0)


# ---------------------------------------------------------------------------
# ModelConfig discriminated union
# ---------------------------------------------------------------------------


def test_ModelConfig_parses_openai_from_dict() -> None:
    """ModelConfig union dispatches to OpenAIConfig based on provider field."""
    adapter = TypeAdapter(ModelConfig)

    config = adapter.validate_python({"provider": "openai", "model": "gpt-4o"})

    assert isinstance(config, OpenAIConfig)
    assert config.model == "gpt-4o"


def test_ModelConfig_parses_anthropic_from_dict() -> None:
    """ModelConfig union dispatches to AnthropicConfig based on provider field."""
    adapter = TypeAdapter(ModelConfig)

    config = adapter.validate_python({"provider": "anthropic", "model": "claude-sonnet-4-6"})

    assert isinstance(config, AnthropicConfig)


def test_ModelConfig_rejects_unknown_provider() -> None:
    """Unknown provider in discriminated union raises ValidationError."""
    adapter = TypeAdapter(ModelConfig)

    with pytest.raises(ValidationError):
        adapter.validate_python({"provider": "fake", "model": "x"})


# ---------------------------------------------------------------------------
# RuntimeConfig
# ---------------------------------------------------------------------------


def test_RuntimeConfig_defaults() -> None:
    """RuntimeConfig has sensible defaults."""
    config = RuntimeConfig()

    assert config.timeout is None
    assert config.max_retries == 2


def test_RuntimeConfig_timeout_must_be_positive() -> None:
    """Timeout must be > 0."""
    with pytest.raises(ValidationError):
        RuntimeConfig(timeout=0)


def test_RuntimeConfig_max_retries_must_be_non_negative() -> None:
    """max_retries must be >= 0."""
    with pytest.raises(ValidationError):
        RuntimeConfig(max_retries=-1)
