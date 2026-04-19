"""Map our ``ModelConfig`` + ``RuntimeConfig`` to ``litellm.completion`` kwargs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openfactcheck.chat.config import OpenAIConfig

if TYPE_CHECKING:
    from openfactcheck.chat.config import AnthropicConfig, ModelConfig, RuntimeConfig

type Kwargs = dict[str, Any]
"""Keyword arguments for ``litellm.completion`` / ``litellm.acompletion``.

``Any`` is intentional: the dict is spread into litellm's completion
function, whose params have many specific types. A stricter value type
would force explicit casts at every call site.
"""


def _set_optional(params: Kwargs, key: str, value: object) -> None:
    """Set ``key`` on ``params`` only if ``value`` is not None."""
    if value is not None:
        params[key] = value


def _common_kwargs(config: ModelConfig, runtime: RuntimeConfig) -> Kwargs:
    """Kwargs shared by every provider.

    litellm uses model strings of the form ``"<provider>/<model>"``, which
    matches our ``config.provider + config.model`` directly.
    """
    params: Kwargs = {
        "model": f"{config.provider}/{config.model}",
        "num_retries": runtime.max_retries,
    }
    _set_optional(params, "temperature", config.temperature)
    _set_optional(params, "max_tokens", config.max_output_tokens)
    _set_optional(params, "top_p", config.top_p)
    _set_optional(params, "timeout", runtime.timeout)
    return params


def _openai_kwargs(config: OpenAIConfig) -> Kwargs:
    """OpenAI-specific kwargs."""
    params: Kwargs = {}
    _set_optional(params, "seed", config.seed)
    _set_optional(params, "frequency_penalty", config.frequency_penalty)
    _set_optional(params, "presence_penalty", config.presence_penalty)
    _set_optional(params, "reasoning_effort", config.reasoning_effort)
    return params


def _anthropic_kwargs(config: AnthropicConfig) -> Kwargs:
    """Anthropic-specific kwargs."""
    params: Kwargs = {}
    _set_optional(params, "top_k", config.top_k)
    if config.thinking and config.thinking_budget_tokens is not None:
        params["thinking"] = {"type": "enabled", "budget_tokens": config.thinking_budget_tokens}
    return params


def config_to_kwargs(config: ModelConfig, runtime: RuntimeConfig) -> Kwargs:
    """Translate our typed config to kwargs for ``litellm.completion``."""
    params = _common_kwargs(config, runtime)
    if isinstance(config, OpenAIConfig):
        params.update(_openai_kwargs(config))
    else:
        params.update(_anthropic_kwargs(config))
    return params
