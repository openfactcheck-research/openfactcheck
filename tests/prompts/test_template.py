"""Tests for PromptTemplate: construction, filling, and the variable contract."""

from __future__ import annotations

import pytest

from openfactcheck.chat import SystemMessage, UserMessage
from openfactcheck.prompts import (
    Prompt,
    PromptTemplate,
    PromptValidationError,
    PromptVariableError,
    VariableSpec,
)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_PromptTemplate_from_messages_tuple_shorthand() -> None:
    """(role, text) tuples become the matching chat messages."""
    template = PromptTemplate.from_messages(
        [("system", "You verify."), ("user", "Claim: {{claim}}")],
        name="verifier",
    )

    assert [type(m).__name__ for m in template.messages] == ["SystemMessage", "UserMessage"]
    assert list(template.variables) == ["claim"]


def test_PromptTemplate_from_messages_accepts_message_objects() -> None:
    """Chat message objects pass through unchanged."""
    template = PromptTemplate.from_messages(
        [SystemMessage(content="S"), UserMessage(content="{{x}}")],
        name="t",
    )

    assert isinstance(template.messages[0], SystemMessage)
    assert list(template.variables) == ["x"]


def test_PromptTemplate_from_messages_infers_required_variables() -> None:
    """Without an explicit contract, placeholders are inferred as required strings."""
    template = PromptTemplate.from_messages([("user", "{{a}} {{b}}")], name="t")

    assert set(template.variables) == {"a", "b"}
    assert all(spec.required for spec in template.variables.values())


def test_PromptTemplate_from_template_single_message() -> None:
    """from_template builds a one-message template defaulting to the user role."""
    template = PromptTemplate.from_template("Hi {{name}}", name="greet")

    assert len(template.messages) == 1
    assert template.messages[0].role == "user"


def test_PromptTemplate_allows_repeated_roles() -> None:
    """Few-shot user/assistant pairs are accepted."""
    template = PromptTemplate.from_messages(
        [("user", "q1"), ("assistant", "a1"), ("user", "q2"), ("assistant", "a2")],
        name="fewshot",
    )

    assert [m.role for m in template.messages] == ["user", "assistant", "user", "assistant"]


# ---------------------------------------------------------------------------
# Contract validation
# ---------------------------------------------------------------------------


def test_PromptTemplate_undeclared_placeholder_rejected() -> None:
    """An explicit contract that omits a referenced placeholder is rejected."""
    with pytest.raises(PromptValidationError, match="undeclared variable"):
        PromptTemplate.from_messages([("user", "{{name}}")], name="t", variables={})


def test_PromptTemplate_declared_unused_variable_allowed() -> None:
    """A declared variable that no message references is allowed."""
    template = PromptTemplate.from_messages(
        [("user", "no placeholders")],
        name="t",
        variables={"future": VariableSpec.string("future")},
    )

    assert "future" in template.variables


def test_PromptTemplate_invalid_name_rejected() -> None:
    """A non-identifier name is rejected."""
    with pytest.raises(PromptValidationError):
        PromptTemplate.from_messages([("user", "x")], name="not a name")


def test_PromptTemplate_equality_excludes_metadata() -> None:
    """Two structurally-equal templates compare equal despite differing metadata."""
    a = PromptTemplate.from_messages([("user", "{{x}}")], name="t", metadata={"source": "a"})
    b = PromptTemplate.from_messages([("user", "{{x}}")], name="t", metadata={"source": "b"})

    assert a == b


# ---------------------------------------------------------------------------
# Filling
# ---------------------------------------------------------------------------


def test_PromptTemplate_to_prompt_returns_filled_prompt() -> None:
    """to_prompt substitutes values and returns a Prompt carrying provenance."""
    template = PromptTemplate.from_messages([("user", "Claim: {{claim}}")], name="v")

    prompt = template.to_prompt(claim="X")

    assert isinstance(prompt, Prompt)
    assert prompt.name == "v"
    assert prompt.messages[0].content == "Claim: X"
    assert dict(prompt.variables_used) == {"claim": "X"}


def test_PromptTemplate_to_messages_returns_chat_messages() -> None:
    """to_messages fills and returns chat message objects."""
    template = PromptTemplate.from_messages([("system", "S"), ("user", "{{x}}")], name="t")

    messages = template.to_messages(x="hi")

    assert [m.content for m in messages] == ["S", "hi"]
    assert isinstance(messages[1], UserMessage)


def test_PromptTemplate_to_string_is_role_labeled() -> None:
    """to_string joins role-labeled lines with blank lines."""
    template = PromptTemplate.from_messages([("system", "S"), ("user", "{{x}}")], name="t")

    assert template.to_string(x="hi") == "system: S\n\nuser: hi"


def test_PromptTemplate_optional_variable_uses_default() -> None:
    """An omitted optional variable falls back to its default; supplying overrides it."""
    template = PromptTemplate.from_messages(
        [("user", "Tone: {{tone}}")],
        name="t",
        variables={"tone": VariableSpec.string("tone", required=False, default="neutral")},
    )

    assert template.to_string(tone="formal") == "user: Tone: formal"
    assert template.to_string() == "user: Tone: neutral"


# ---------------------------------------------------------------------------
# Variable errors
# ---------------------------------------------------------------------------


def test_PromptTemplate_to_prompt_missing_required_raises() -> None:
    """A missing required variable raises PromptVariableError."""
    template = PromptTemplate.from_messages([("user", "{{a}} {{b}}")], name="t")

    with pytest.raises(PromptVariableError) as exc:
        template.to_prompt(a="1")

    assert exc.value.missing == ("b",)


def test_PromptTemplate_to_prompt_unexpected_variable_raises() -> None:
    """An unexpected variable raises PromptVariableError."""
    template = PromptTemplate.from_messages([("user", "{{a}}")], name="t")

    with pytest.raises(PromptVariableError) as exc:
        template.to_prompt(a="1", b="2")

    assert exc.value.unexpected == ("b",)
