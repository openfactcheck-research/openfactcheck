"""Tests for MarkdownPromptCodec — decode, encode, round-trip, v1 policies."""

from __future__ import annotations

from textwrap import dedent

import pytest

from openfactcheck.prompts import (
    MarkdownPromptCodec,
    PromptFormatError,
    PromptTemplate,
    PromptValidationError,
    VariableSpec,
)


def _decode(text: str, *, name_hint: str | None = None) -> PromptTemplate:
    return MarkdownPromptCodec().decode(dedent(text).lstrip("\n"), name_hint=name_hint)


# ---------------------------------------------------------------------------
# Frontmatter.
# ---------------------------------------------------------------------------


def test_decode_frontmatter_happy_path() -> None:
    """A well-formed frontmatter + body decodes into a Prompt."""
    prompt = _decode(
        """
        ---
        name: sample
        version: 2
        description: a sample prompt
        variables:
          claim:
            type: string
            required: true
        ---

        <user>

        # User Prompt

        Claim: {{claim}}

        </user>
        """
    )

    assert prompt.name == "sample"
    assert prompt.description == "a sample prompt"
    assert prompt.metadata.get("version") == 2
    assert set(prompt.variables) == {"claim"}


def test_decode_missing_name_rejected() -> None:
    """Frontmatter without ``name`` → PromptFormatError."""
    with pytest.raises(PromptFormatError, match="missing required 'name'"):
        _decode(
            """
            ---
            description: no name
            ---

            <user>

            # User Prompt

            hi

            </user>
            """
        )


def test_decode_unknown_frontmatter_key_rejected() -> None:
    """Unknown top-level frontmatter keys are rejected."""
    with pytest.raises(PromptFormatError, match="unknown key"):
        _decode(
            """
            ---
            name: sample
            model: gpt-4o
            ---

            <user>

            # User Prompt

            hi

            </user>
            """
        )


def test_decode_malformed_yaml() -> None:
    """Invalid YAML frontmatter → PromptFormatError."""
    with pytest.raises(PromptFormatError, match="not valid YAML"):
        _decode(
            """
            ---
            name: sample
              version: "unclosed
            ---

            <user>

            # User Prompt

            hi

            </user>
            """
        )


def test_decode_frontmatter_not_closed() -> None:
    """Missing closing frontmatter delimiter is rejected."""
    with pytest.raises(PromptFormatError, match="not closed"):
        _decode(
            """
            ---
            name: sample
            """
        )


def test_decode_name_hint_mismatch_rejected() -> None:
    """If name_hint is supplied and disagrees with frontmatter name, PromptFormatError."""
    with pytest.raises(PromptFormatError, match="does not match name_hint"):
        _decode(
            """
            ---
            name: verifier
            ---

            <user>

            # User Prompt

            hi

            </user>
            """,
            name_hint="extractor",
        )


# ---------------------------------------------------------------------------
# Tag structure.
# ---------------------------------------------------------------------------


def test_decode_tag_in_paragraph_is_content() -> None:
    """Literal ``<system>`` inside a paragraph stays as content, not structure."""
    prompt = _decode(
        """
        ---
        name: sample
        ---

        <user>

        # User Prompt

        The literal <system> tag inside a paragraph stays as content.

        </user>
        """
    )

    assert "<system>" in prompt.messages[0].content


def test_decode_tag_in_code_fence_is_content() -> None:
    """Tags inside a fenced code block are preserved."""
    prompt = _decode(
        """
        ---
        name: sample
        ---

        <user>

        # User Prompt

        ```xml
        <system>not a tag</system>
        ```

        </user>
        """
    )

    assert "<system>not a tag</system>" in prompt.messages[0].content


def test_decode_nested_tag_rejected() -> None:
    """Opening a new role block while another is open → PromptFormatError."""
    with pytest.raises(PromptFormatError, match="still open"):
        _decode(
            """
            ---
            name: sample
            ---

            <system>

            # System Prompt

            body

            <user>
            """
        )


def test_decode_mismatched_closer_rejected() -> None:
    """Closing tag that doesn't match the opening → PromptFormatError."""
    with pytest.raises(PromptFormatError, match="mismatched closing tag"):
        _decode(
            """
            ---
            name: sample
            ---

            <system>

            # System Prompt

            body

            </user>
            """
        )


def test_decode_missing_closer_rejected() -> None:
    """Unclosed role block is rejected."""
    with pytest.raises(PromptFormatError, match="not closed"):
        _decode(
            """
            ---
            name: sample
            ---

            <system>

            # System Prompt

            body
            """
        )


def test_decode_zero_blocks_rejected() -> None:
    """A body with no role blocks is rejected."""
    with pytest.raises(PromptFormatError, match="no role blocks"):
        _decode(
            """
            ---
            name: sample
            ---

            Just documentation; no role blocks.
            """
        )


def test_decode_duplicate_role_rejected() -> None:
    """Markdown codec v1 rejects duplicate roles (codec policy, not domain)."""
    with pytest.raises(PromptFormatError, match="duplicate"):
        _decode(
            """
            ---
            name: sample
            ---

            <user>

            # User Prompt

            one

            </user>

            <user>

            # User Prompt

            two

            </user>
            """
        )


# ---------------------------------------------------------------------------
# H1 rule.
# ---------------------------------------------------------------------------


def test_decode_h1_required_and_stripped() -> None:
    """H1 is verified then stripped from the rendered template."""
    prompt = _decode(
        """
        ---
        name: sample
        ---

        <system>

        # System Prompt

        body content

        </system>
        """
    )

    content = prompt.messages[0].content
    assert "# System Prompt" not in content
    assert content == "body content"


def test_decode_h1_missing_rejected() -> None:
    """Missing H1 in a block → PromptFormatError."""
    with pytest.raises(PromptFormatError, match="first non-blank line"):
        _decode(
            """
            ---
            name: sample
            ---

            <system>

            body without H1

            </system>
            """
        )


def test_decode_h1_wrong_role_rejected() -> None:
    """H1 that names the wrong role → PromptFormatError."""
    with pytest.raises(PromptFormatError, match="first non-blank line"):
        _decode(
            """
            ---
            name: sample
            ---

            <system>

            # User Prompt

            body

            </system>
            """
        )


# ---------------------------------------------------------------------------
# Variable contract — domain invariant.
# ---------------------------------------------------------------------------


def test_decode_undeclared_placeholder_rejected_as_validation_error() -> None:
    """Placeholder with no matching variables entry raises PromptValidationError (domain, not codec)."""
    with pytest.raises(PromptValidationError, match="undeclared variable"):
        _decode(
            """
            ---
            name: sample
            variables:
              evidence:
                type: string
                required: true
            ---

            <user>

            # User Prompt

            Claim: {{claim}}
            Evidence: {{evidence}}

            </user>
            """
        )


# ---------------------------------------------------------------------------
# Encode / round-trip.
# ---------------------------------------------------------------------------


def test_encode_round_trips_through_decode() -> None:
    """``encode`` then ``decode`` yields an equal template."""
    original = PromptTemplate.from_messages(
        [("system", "You are helpful."), ("user", "Hi {{name}}")],
        name="greeter",
        description="Greet a user by name.",
        variables={"name": VariableSpec.string("name")},
    )

    codec = MarkdownPromptCodec()
    encoded = codec.encode(original)
    decoded = codec.decode(encoded)

    assert original == decoded


def test_encode_emits_every_frontmatter_field() -> None:
    """Encoded output contains name + description + variables + body blocks."""
    template = PromptTemplate.from_messages(
        [("user", "Hi {{name}}")],
        name="greeter",
        description="Say hi.",
        variables={"name": VariableSpec.string("name")},
    )

    encoded = MarkdownPromptCodec().encode(template)

    assert "name: greeter" in encoded
    assert "description: Say hi." in encoded
    assert "<user>" in encoded
    assert "</user>" in encoded
    assert "# User Prompt" in encoded


def test_encode_rejects_repeated_roles() -> None:
    """The markdown codec cannot encode a template with repeated roles."""
    template = PromptTemplate.from_messages(
        [("user", "a"), ("user", "b")],
        name="sample",
    )
    with pytest.raises(PromptFormatError, match="repeated role"):
        MarkdownPromptCodec().encode(template)
