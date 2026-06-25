"""Tests for ModelSpec and its resolution to a provider config."""

import pytest

from openfactcheck.chat.config import AnthropicConfig, OpenAIConfig, OpenRouterConfig
from openfactcheck.config import ModelSpec
from openfactcheck.config.errors import ConfigError


@pytest.mark.parametrize(
    "name, provider, model",
    [
        ("gpt-4o", "openai", "gpt-4o"),
        ("openai/gpt-4o", "openai", "gpt-4o"),
        ("anthropic/claude-sonnet-4-6", "anthropic", "claude-sonnet-4-6"),
        ("openrouter/meta-llama/llama-4", "openrouter", "meta-llama/llama-4"),
        ("meta-llama/llama-4", "openai", "meta-llama/llama-4"),
        ("  anthropic/claude-sonnet-4-6  ", "anthropic", "claude-sonnet-4-6"),
    ],
)
def test_ModelSpec_to_model_config_resolves_provider(name: str, provider: str, model: str) -> None:
    """A known provider prefix selects the provider; the remainder is the model id."""
    config = ModelSpec(name=name).to_model_config()

    assert config.provider == provider
    assert config.model == model


def test_ModelSpec_to_model_config_uses_fallback() -> None:
    """An unset name falls back to the supplied default."""
    config = ModelSpec(temperature=0.2).to_model_config(fallback_name="gpt-4o-mini")

    assert isinstance(config, OpenAIConfig)
    assert config.model == "gpt-4o-mini"
    assert config.temperature == 0.2


def test_ModelSpec_to_model_config_name_overrides_fallback() -> None:
    """A set name wins over the fallback."""
    config = ModelSpec(name="anthropic/claude-sonnet-4-6").to_model_config(fallback_name="gpt-4o")

    assert isinstance(config, AnthropicConfig)
    assert config.model == "claude-sonnet-4-6"


@pytest.mark.parametrize("spec", [ModelSpec(), ModelSpec(name="   ")])
def test_ModelSpec_to_model_config_no_name(spec: ModelSpec) -> None:
    """With no name in the spec and no fallback, resolution raises."""
    with pytest.raises(ConfigError, match="no model name"):
        spec.to_model_config()


def test_ModelSpec_to_model_config_openrouter_keeps_namespace() -> None:
    """An openrouter prefix keeps the namespaced model id."""
    config = ModelSpec(name="openrouter/meta-llama/llama-4").to_model_config()

    assert isinstance(config, OpenRouterConfig)
    assert config.model == "meta-llama/llama-4"


def test_ModelSpec_to_model_config_applies_sampling() -> None:
    """Set sampling parameters flow into the provider config."""
    config = ModelSpec(name="gpt-4o", temperature=0.2, max_output_tokens=500).to_model_config()

    assert isinstance(config, OpenAIConfig)
    assert config.temperature == 0.2
    assert config.max_output_tokens == 500


def test_ModelSpec_to_model_config_anthropic_params() -> None:
    """Anthropic-only knobs reach the Anthropic config."""
    config = ModelSpec(name="anthropic/claude-sonnet-4-6", top_k=10).to_model_config()

    assert isinstance(config, AnthropicConfig)
    assert config.top_k == 10


def test_ModelSpec_to_model_config_drops_none() -> None:
    """A param set to None is dropped, so it never trips the provider's check."""
    config = ModelSpec(name="gpt-4o", temperature=None, top_k=None).to_model_config()

    assert isinstance(config, OpenAIConfig)
    assert config.temperature is None


def test_ModelSpec_to_model_config_wrong_provider_param() -> None:
    """A param the resolved provider does not accept raises a clear, contextual error."""
    with pytest.raises(ConfigError, match="invalid configuration for model 'gpt-4o'") as exc_info:
        ModelSpec(name="openai/gpt-4o", top_k=10).to_model_config()

    message = str(exc_info.value)
    assert "openai" in message
    assert "top_k" in message


def test_ModelSpec_to_model_config_out_of_range_param() -> None:
    """A param that violates the provider's constraints raises with the field and reason."""
    with pytest.raises(ConfigError, match="temperature"):
        ModelSpec(name="gpt-4o", temperature=5.0).to_model_config()
