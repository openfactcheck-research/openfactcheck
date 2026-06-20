"""The transcribed RARR prompts load and fill cleanly."""

from pathlib import Path

import pytest

import openfactcheck.components.rarr as rarr_pkg
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(rarr_pkg.__file__).resolve().parent / "prompts"

_EVIDENCE = "The Eiffel Tower was completed in 1889."


@pytest.mark.parametrize(
    ("filename", "values"),
    [
        ("query_generator.md", {"input": "The Eiffel Tower was completed in 1850."}),
        ("agreement_gate.md", {"claim": "Completed in 1850.", "query": "When was it completed?", "evidence": _EVIDENCE}),
        ("editor.md", {"claim": "Completed in 1850.", "query": "When was it completed?", "evidence": _EVIDENCE}),
    ],
)
def test_rarr_prompt_loads_and_fills(filename: str, values: dict[str, str]) -> None:
    template = PromptTemplate.from_file(_PROMPTS_DIR / filename)

    messages = template.to_messages(**values)

    assert len(messages) == 2  # noqa: PLR2004 - a system and a user message.
    rendered = "\n".join(message.content for message in messages)
    assert "{{" not in rendered  # every placeholder was substituted
