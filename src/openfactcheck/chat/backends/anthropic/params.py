"""Map our ``ModelConfig`` to Anthropic SDK ``messages.create`` kwargs.

``RuntimeConfig`` (timeout, retries) is applied at client construction in
``openfactcheck.chat.backends.anthropic.backend``, not in the messages call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openfactcheck.chat.config import AnthropicConfig
from openfactcheck.chat.errors import ProviderError, UnsupportedFeatureError

if TYPE_CHECKING:
    from openfactcheck.chat.config import ModelConfig

type Kwargs = dict[str, Any]
"""Keyword arguments for ``anthropic.messages.create``.

``Any`` is intentional: the dict is spread into the SDK call, which
accepts many specific types. A stricter value type would force explicit
casts at every call site.
"""


def _set_optional(params: Kwargs, key: str, value: object) -> None:
    """Set ``key`` on ``params`` only if ``value`` is not None."""
    if value is not None:
        params[key] = value


def config_to_kwargs(config: ModelConfig) -> Kwargs:
    """Translate our typed config to kwargs for ``anthropic.messages.create``.

    The direct Anthropic SDK backend only supports ``AnthropicConfig``.
    Passing any other provider config raises
    [`UnsupportedFeatureError`][UnsupportedFeatureError].
    """
    if not isinstance(config, AnthropicConfig):
        raise UnsupportedFeatureError(
            f"Anthropic backend does not support provider '{config.provider}'. "
            f"Use the LangChain or litellm backend for multi-provider support."
        )
    if config.max_output_tokens is None:
        # Provider-level validation normally catches this at ChatClient construction.
        # Backstop for callers who use AnthropicBackend directly.
        raise ProviderError("Anthropic requires max_output_tokens; set it on AnthropicConfig.")

    params: Kwargs = {"model": config.model, "max_tokens": config.max_output_tokens}
    _set_optional(params, "temperature", config.temperature)
    _set_optional(params, "top_p", config.top_p)
    _set_optional(params, "top_k", config.top_k)
    if config.thinking and config.thinking_budget_tokens is not None:
        params["thinking"] = {"type": "enabled", "budget_tokens": config.thinking_budget_tokens}
    return params
