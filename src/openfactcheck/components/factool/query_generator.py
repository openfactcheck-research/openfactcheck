"""Factool query generator."""

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.prompts import PromptTemplate
from openfactcheck.types import Claim, Query

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class _GeneratedQueries(BaseModel):
    """Structured output: the search queries generated for a claim."""

    queries: list[str]


@dataclass(frozen=True, slots=True)
class FactoolQueryGenerator:
    """Generate skeptical search queries for a claim, following Factool's method.

    Prompts the model for concise search-engine queries aimed at verifying the
    claim.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(
        default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "query_generator.md")
    )
    """The query-generation prompt. Defaults to Factool's; override to customise."""

    async def __call__(self, claim: Claim) -> Query:
        """Generate search queries for ``claim``.

        Args:
            claim: Claim to generate queries for.

        Returns:
            The claim paired with the generated search questions.
        """
        messages = self.prompt.to_messages(input=claim.text)
        generated = await self.client.acompletion_as(messages, _GeneratedQueries)
        return Query(claim=claim, questions=generated.queries)
