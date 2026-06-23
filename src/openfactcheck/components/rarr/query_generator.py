"""RARR query generator."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Claim, Query
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

DEFAULT_NUM_ROUNDS = 3
"""Default number of times the questions are sampled before taking their union."""


class RARRQueryGeneratorModel(BaseModel):
    """RARR's structured comprehensive-question-generation result.

    The query generator unions these across sampling rounds and maps them onto a
    [`Query`][Query]. It is also the value handed
    to a call's ``on_partial`` hook, the question list growing as the model writes it.
    """

    questions: list[str]


@dataclass(frozen=True, slots=True)
class RARRQueryGenerator:
    """Generate comprehensive verification questions for a passage, following RARR's method.

    Prompts the model for the questions a reader would look up to check the
    passage. To widen coverage, it samples the model several times and takes the
    union of the questions, deduplicating while keeping first-seen order. Sampling
    benefits from a chat client with a non-zero temperature.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(
        default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "query_generator.md")
    )
    """The question-generation prompt. Defaults to RARR's; override to customise."""

    num_rounds: int = DEFAULT_NUM_ROUNDS
    """How many times to sample questions before taking their union."""

    async def __call__(
        self,
        claim: Claim,
        *,
        on_partial: Callable[[RARRQueryGeneratorModel], None] | None = None,
    ) -> Query:
        """Generate verification questions for ``claim``.

        Args:
            claim: The passage to generate questions for.
            on_partial: Called with the questions of the current sampling round as
                they stream in. Omit it for non-streaming calls. The returned
                query is the union across all rounds either way.

        Returns:
            The claim paired with the unioned verification questions.
        """
        messages = self.prompt.to_messages(input=claim.text)
        seen: dict[str, None] = {}
        for _ in range(self.num_rounds):
            result = (
                await self.client.acompletion_as(messages, RARRQueryGeneratorModel)
                if on_partial is None
                else await self._stream(messages, on_partial)
            )
            for question in result.questions:
                if stripped := question.strip():
                    seen.setdefault(stripped, None)
        return Query(claim=claim, questions=list(seen))

    async def _stream(
        self, messages: list[Message], on_partial: Callable[[RARRQueryGeneratorModel], None]
    ) -> RARRQueryGeneratorModel:
        """Stream one sampling round, forwarding each partial result to ``on_partial``."""
        result: RARRQueryGeneratorModel | None = None
        async for partial in self.client.astream_as(messages, RARRQueryGeneratorModel):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("query generator stream produced no value")
        return result
