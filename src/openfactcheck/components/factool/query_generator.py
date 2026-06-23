"""Factool query generator."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Claim, Query
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class FactoolQueryGeneratorModel(BaseModel):
    """Factool's structured query-generation result.

    The query generator maps this onto a [`Query`][Query]. It
    is also the value handed to a call's ``on_partial`` hook, the query list
    growing as the model writes it.
    """

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

    async def __call__(
        self,
        claim: Claim,
        *,
        on_partial: Callable[[FactoolQueryGeneratorModel], None] | None = None,
    ) -> Query:
        """Generate search queries for ``claim``.

        Args:
            claim: Claim to generate queries for.
            on_partial: Called with the generated queries as they stream in, each
                call carrying the queries produced so far. Omit it for a single
                non-streaming call. The returned query is the same either way.

        Returns:
            The claim paired with the generated search questions.
        """
        messages = self.prompt.to_messages(input=claim.text)
        result = (
            await self.client.acompletion_as(messages, FactoolQueryGeneratorModel)
            if on_partial is None
            else await self._stream(messages, on_partial)
        )
        return Query(claim=claim, questions=result.queries)

    async def _stream(
        self, messages: list[Message], on_partial: Callable[[FactoolQueryGeneratorModel], None]
    ) -> FactoolQueryGeneratorModel:
        """Stream the query generation, forwarding each partial result to ``on_partial``."""
        result: FactoolQueryGeneratorModel | None = None
        async for partial in self.client.astream_as(messages, FactoolQueryGeneratorModel):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("query generator stream produced no value")
        return result
