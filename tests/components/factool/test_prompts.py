"""The transcribed Factool prompts load and fill cleanly."""

from pathlib import Path

import pytest

import openfactcheck.components.factool as factool_pkg
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(factool_pkg.__file__).resolve().parent / "prompts"


@pytest.mark.parametrize(
    ("filename", "values"),
    [
        ("claim_processor.md", {"input": "The earth is flat."}),
        ("query_generator.md", {"input": "The earth is flat."}),
        ("verifier.md", {"claim": "The earth is flat.", "evidence": "['The earth is an oblate spheroid.']"}),
    ],
)
def test_factool_prompt_loads_and_fills(filename: str, values: dict[str, str]) -> None:
    template = PromptTemplate.from_file(_PROMPTS_DIR / filename)

    messages = template.to_messages(**values)

    assert len(messages) == 2  # noqa: PLR2004 - a system and a user message.
    rendered = "\n".join(message.content for message in messages)
    assert "{{" not in rendered  # every placeholder was substituted
