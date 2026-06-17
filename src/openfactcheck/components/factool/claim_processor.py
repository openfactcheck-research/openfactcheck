"""Factool claim processor."""

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.prompts import PromptTemplate
from openfactcheck.types import Claim, Input

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class _ClaimExtraction(BaseModel):
    """Structured output: the claims extracted from a piece of text."""

    claims: list[str]


@dataclass(frozen=True, slots=True)
class FactoolClaimProcessor:
    """Extract atomic factual claims, following Factool's knowledge-QA method.

    Prompts the model to break the input into short, self-contained claims with
    their coreferences resolved.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(
        default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "claim_processor.md")
    )
    """The claim-extraction prompt. Defaults to Factool's; override to customise."""

    async def __call__(self, text: Input) -> list[Claim]:
        """Extract atomic claims from ``text``.

        Args:
            text: Input text to process into claims.

        Returns:
            The extracted claims; empty when the model finds none.
        """
        messages = self.prompt.to_messages(input=text.content)
        extraction = await self.client.acompletion_as(messages, _ClaimExtraction)
        return [Claim(text=claim) for claim in extraction.claims]
