"""Tests for loading a PromptTemplate from a file or markdown string."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from openfactcheck.prompts import PromptFormatError, PromptNotFoundError, PromptTemplate

if TYPE_CHECKING:
    from pathlib import Path

_MARKDOWN = """\
---
name: greeter
variables:
  who:
    type: string
    required: true
---

<user>

# User Prompt

Hello, {{who}}!

</user>
"""


def test_PromptTemplate_from_file_markdown(tmp_path: Path) -> None:
    """A .md file routes to the markdown codec and decodes to a template."""
    path = tmp_path / "greeter.md"
    path.write_text(_MARKDOWN, encoding="utf-8")

    template = PromptTemplate.from_file(path)

    assert template.name == "greeter"
    assert template.to_string(who="Alice") == "user: Hello, Alice!"


def test_PromptTemplate_from_markdown_string() -> None:
    """from_markdown decodes an in-memory markdown string."""
    template = PromptTemplate.from_markdown(_MARKDOWN)

    assert template.name == "greeter"
    assert list(template.variables) == ["who"]


def test_PromptTemplate_from_file_unknown_extension(tmp_path: Path) -> None:
    """An unregistered extension raises PromptFormatError."""
    path = tmp_path / "greeter.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(PromptFormatError, match="no codec"):
        PromptTemplate.from_file(path)


def test_PromptTemplate_from_file_missing(tmp_path: Path) -> None:
    """A nonexistent path raises PromptNotFoundError."""
    with pytest.raises(PromptNotFoundError):
        PromptTemplate.from_file(tmp_path / "nope.md")
