"""Map our ``ModelConfig`` to OpenAI SDK ``chat.completions.create`` kwargs.

``RuntimeConfig`` (timeout, retries) is applied at client construction in
``openfactcheck.chat.backends.openai.backend``, not in the completions call.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from openfactcheck.chat.config import OpenAICompatibleConfig
from openfactcheck.chat.errors import UnsupportedFeatureError

if TYPE_CHECKING:
    from openfactcheck.chat.config import ModelConfig
    from openfactcheck.chat.requests import ResponseFormat

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

    The direct OpenAI SDK backend supports OpenAI-compatible configs
    ([`OpenAIConfig`][OpenAIConfig] and [`OpenRouterConfig`][OpenRouterConfig]).
    Passing any other provider config raises
    [`UnsupportedFeatureError`][UnsupportedFeatureError].
    """
    if not isinstance(config, OpenAICompatibleConfig):
        raise UnsupportedFeatureError(
            f"OpenAI backend does not support provider '{config.provider}'; "
            f"it only accepts OpenAI-compatible configs (OpenAIConfig, OpenRouterConfig)."
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


def response_format_kwargs(response_format: ResponseFormat) -> Kwargs:
    """Build the ``response_format`` kwarg for OpenAI structured output.

    Wraps the schema as a ``json_schema`` response format. When the request
    asks for strict enforcement, the schema is tightened with
    [`to_strict_schema`][openfactcheck.chat.backends.openai.params.to_strict_schema]
    so it satisfies OpenAI's strict-mode requirements.
    """
    schema = to_strict_schema(response_format.json_schema) if response_format.strict else response_format.json_schema
    return {
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": response_format.name,
                "schema": schema,
                "strict": response_format.strict,
            },
        }
    }


_UNSUPPORTED_KEYWORDS = frozenset(
    {
        # Numbers and integers.
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        # Strings.
        "minLength",
        "maxLength",
        "pattern",
        "format",
        # Arrays.
        "minItems",
        "maxItems",
        "uniqueItems",
        # Objects.
        "minProperties",
        "maxProperties",
        "patternProperties",
        "propertyNames",
    }
)
"""Validation keywords outside the strict structured-output subset.

Strict mode does not support these (some providers reject them outright, for
example Anthropic on numeric ranges). They are dropped from the wire schema;
the constraints still hold because the reply is validated against the original
model, with reprompts on failure.
"""


def to_strict_schema(schema: dict[str, object]) -> dict[str, object]:
    """Return a deep copy of a JSON Schema tightened for strict structured output.

    Strict mode requires every object to set ``additionalProperties: false`` and
    to list all of its properties as ``required``. This walks the schema
    (including ``$defs`` and nested objects), applies both, and drops validation
    keywords outside the supported subset (numeric ranges, string patterns, and
    so on). The input is left untouched.
    """
    result = deepcopy(schema)
    _tighten(result)
    return result


def _tighten(node: object) -> None:
    """Recursively enforce strict-object rules on a JSON Schema node, in place."""
    if isinstance(node, dict):
        obj = cast("dict[str, object]", node)
        for keyword in _UNSUPPORTED_KEYWORDS & obj.keys():
            del obj[keyword]
        props = obj.get("properties")
        if obj.get("type") == "object" and isinstance(props, dict):
            obj["additionalProperties"] = False
            obj["required"] = list(cast("dict[str, object]", props).keys())
        for value in obj.values():
            _tighten(value)
    elif isinstance(node, list):
        for item in cast("list[object]", node):
            _tighten(item)
