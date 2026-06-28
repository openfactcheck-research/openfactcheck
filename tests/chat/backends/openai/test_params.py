"""Tests for OpenAI backend param mapping."""

import pytest

from openfactcheck.chat.backends.openai.params import config_to_kwargs, response_format_kwargs, to_strict_schema
from openfactcheck.chat.config import AnthropicConfig, OpenAIConfig, OpenRouterConfig
from openfactcheck.chat.errors import UnsupportedFeatureError
from openfactcheck.chat.requests import ResponseFormat


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
    assert kwargs["max_completion_tokens"] == 100
    assert "max_tokens" not in kwargs
    assert kwargs["top_p"] == 0.9
    assert kwargs["seed"] == 42
    assert kwargs["frequency_penalty"] == 0.5
    assert kwargs["presence_penalty"] == 0.2
    assert kwargs["reasoning_effort"] == "medium"


def test_config_to_kwargs_openrouter_uses_max_completion_tokens() -> None:
    """OpenRouter also uses ``max_completion_tokens`` (the legacy name is deprecated)."""
    config = OpenRouterConfig(model="openai/gpt-4o", max_output_tokens=100)

    kwargs = config_to_kwargs(config)

    assert kwargs["max_completion_tokens"] == 100
    assert "max_tokens" not in kwargs


def test_config_to_kwargs_rejects_anthropic() -> None:
    """Direct OpenAI backend refuses non-OpenAI configs."""
    config = AnthropicConfig(model="claude-sonnet-4-6")

    with pytest.raises(UnsupportedFeatureError, match="does not support provider 'anthropic'"):
        config_to_kwargs(config)


def test_to_strict_schema_tightens_objects() -> None:
    """Strict transform sets additionalProperties=false and requires every property, including in $defs."""
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "pet": {"$ref": "#/$defs/Pet"},
        },
        "required": ["name"],
        "$defs": {
            "Pet": {
                "type": "object",
                "properties": {"species": {"type": "string"}},
            }
        },
    }

    strict = to_strict_schema(schema)

    assert strict["additionalProperties"] is False
    assert sorted(strict["required"]) == ["name", "pet"]
    pet = strict["$defs"]["Pet"]
    assert pet["additionalProperties"] is False
    assert pet["required"] == ["species"]
    # Original is untouched.
    assert "additionalProperties" not in schema


def test_to_strict_schema_drops_unsupported_keywords() -> None:
    """Constraint keywords outside the strict subset are stripped from the wire schema."""
    schema = {
        "type": "object",
        "properties": {
            "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "name": {"type": "string", "maxLength": 50, "pattern": "^x"},
            "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
    }

    strict = to_strict_schema(schema)

    assert "minimum" not in strict["properties"]["score"]
    assert "maximum" not in strict["properties"]["score"]
    assert "maxLength" not in strict["properties"]["name"]
    assert "pattern" not in strict["properties"]["name"]
    assert "minItems" not in strict["properties"]["tags"]
    # The underlying type information is preserved.
    assert strict["properties"]["score"]["type"] == "number"


def test_response_format_kwargs_strict() -> None:
    """A strict ResponseFormat becomes a json_schema response_format with a tightened schema."""
    response_format = ResponseFormat(
        name="Person",
        json_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        strict=True,
    )

    kwargs = response_format_kwargs(response_format)

    block = kwargs["response_format"]
    assert block["type"] == "json_schema"
    assert block["json_schema"]["name"] == "Person"
    assert block["json_schema"]["strict"] is True
    assert block["json_schema"]["schema"]["additionalProperties"] is False


def test_response_format_kwargs_non_strict_skips_transform() -> None:
    """A non-strict ResponseFormat passes the schema through unchanged."""
    response_format = ResponseFormat(
        name="Person",
        json_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        strict=False,
    )

    kwargs = response_format_kwargs(response_format)

    schema = kwargs["response_format"]["json_schema"]["schema"]
    assert "additionalProperties" not in schema
