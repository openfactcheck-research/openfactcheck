"""Map our ``ModelConfig`` to OpenAI SDK ``chat.completions.create`` kwargs.

``RuntimeConfig`` (timeout, retries) is applied at client construction in
``openfactcheck.chat.backends.openai.backend``, not in the completions call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openfactcheck.chat.config import OpenAIConfig
from openfactcheck.chat.errors import UnsupportedFeatureError

if TYPE_CHECKING:
    from openfactcheck.chat.config import ModelConfig

type Kwargs = dict[str, Any]
"""Keyword arguments for ``openai.chat.completions.create``.

``Any`` is intentional: the dict is spread into the SDK call, which
accepts many specific types. A stricter value type would force explicit
casts at every call site.
"""


def _set_optional(params: Kwargs, key: str, value: object) -> None:
    """Set ``key`` on ``params`` only if ``value`` is not None."""
    if value is not None:
        params[key] = value


def config_to_kwargs(config: ModelConfig) -> Kwargs:
    """Translate our typed config to kwargs for ``openai.chat.completions.create``.

    The direct OpenAI SDK backend only supports ``OpenAIConfig``. Passing
    any other provider config raises
    [`UnsupportedFeatureError`][UnsupportedFeatureError].
    """
    if not isinstance(config, OpenAIConfig):
        raise UnsupportedFeatureError(
            f"OpenAI backend does not support provider '{config.provider}'. "
            f"Use the LangChain or litellm backend for multi-provider support."
        )

    params: Kwargs = {"model": config.model}
    _set_optional(params, "temperature", config.temperature)
    _set_optional(params, "max_tokens", config.max_output_tokens)
    _set_optional(params, "top_p", config.top_p)
    _set_optional(params, "seed", config.seed)
    _set_optional(params, "frequency_penalty", config.frequency_penalty)
    _set_optional(params, "presence_penalty", config.presence_penalty)
    _set_optional(params, "reasoning_effort", config.reasoning_effort)
    return params
