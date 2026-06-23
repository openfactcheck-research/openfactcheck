"""The transcribed FactcheckGPT prompts load and fill cleanly."""

from pathlib import Path

import pytest

import openfactcheck.components.factcheckgpt as factcheckgpt_pkg
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(factcheckgpt_pkg.__file__).resolve().parent / "prompts"


@pytest.mark.parametrize(
    ("filename", "values", "num_messages"),
    [
        ("claim_processor.md", {"input": "The earth is flat."}, 2),
        ("claim_decomposer.md", {"input": "The earth is flat."}, 2),
        ("query_generator.md", {"input": "The earth is flat."}, 2),
        ("verifier.md", {"claim": "The earth is flat.", "evidence": "['The earth is an oblate spheroid.']"}, 2),
        ("reviser.md", {"response": "The earth is flat.", "claims": "- The earth is round."}, 2),
    ],
)
def test_factcheckgpt_prompt_loads_and_fills(filename: str, values: dict[str, str], num_messages: int) -> None:
    template = PromptTemplate.from_file(_PROMPTS_DIR / filename)

    messages = template.to_messages(**values)

    assert len(messages) == num_messages
    rendered = "\n".join(message.content for message in messages)
    assert "{{" not in rendered  # every placeholder was substituted
