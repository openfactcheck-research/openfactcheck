"""FactcheckGPT query generator."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Claim, Query
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class FactcheckGPTQueryGeneratorModel(BaseModel):
    """FactcheckGPT's structured query-generator result.

    The query generator maps this onto a [`Query`][Query].
    It is also the value handed to a call's ``on_partial`` hook, the query list
    growing as the model writes it.
    """

    queries: list[str]


@dataclass(frozen=True, slots=True)
class FactcheckGPTQueryGenerator:
    """Generate web search queries for a claim, following FactcheckGPT's method.

    Prompts the model for the search questions a reader would look up to verify
    the claim.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(
        default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "query_generator.md")
    )
    """The query-generation prompt. Defaults to FactcheckGPT's; override to customise."""

    async def __call__(
        self,
        claim: Claim,
        *,
        on_partial: Callable[[FactcheckGPTQueryGeneratorModel], None] | None = None,
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
            await self.client.acompletion_as(messages, FactcheckGPTQueryGeneratorModel)
            if on_partial is None
            else await self._stream(messages, on_partial)
        )
        return Query(claim=claim, questions=result.queries)

    async def _stream(
        self, messages: list[Message], on_partial: Callable[[FactcheckGPTQueryGeneratorModel], None]
    ) -> FactcheckGPTQueryGeneratorModel:
        """Stream the query generation, forwarding each partial result to ``on_partial``."""
        result: FactcheckGPTQueryGeneratorModel | None = None
        async for partial in self.client.astream_as(messages, FactcheckGPTQueryGeneratorModel):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("query generator stream produced no value")
        return result
