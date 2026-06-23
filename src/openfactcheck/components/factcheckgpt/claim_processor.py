"""FactcheckGPT claim processor."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Claim, Input
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class FactcheckGPTClaimProcessorModel(BaseModel):
    """FactcheckGPT's structured claim-processor result.

    The atomic claims the text decomposes into, with a parallel list marking
    whether each is checkworthy; the claim processor keeps only the checkworthy
    ones, mapping them onto [`Claim`][Claim]. It is also the value handed to a
    call's ``on_partial`` hook, the lists growing as the model writes them.
    """

    claims: list[str]
    checkworthy: list[Literal["Yes", "No"]]


@dataclass(frozen=True, slots=True)
class FactcheckGPTClaimProcessor:
    """Decompose text into atomic, checkworthy claims, following FactcheckGPT's method.

    One call decomposes the input into context-independent atomic claims and
    keeps only the ones worth checking, dropping opinions, questions, and other
    non-factual text.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(
        default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "claim_processor.md")
    )
    """The claim-extraction prompt. Defaults to FactcheckGPT's; override to customise."""

    async def __call__(
        self,
        text: Input,
        *,
        on_partial: Callable[[FactcheckGPTClaimProcessorModel], None] | None = None,
    ) -> list[Claim]:
        """Decompose ``text`` into atomic, checkworthy claims.

        Args:
            text: Input text to process into claims.
            on_partial: Called with the extraction as it streams in, each call
                carrying the claims found so far. Omit it for a single
                non-streaming call. The returned claims are the same either way.

        Returns:
            The checkworthy atomic claims; empty when the model finds none.
        """
        messages = self.prompt.to_messages(input=text.content)
        result = (
            await self.client.acompletion_as(messages, FactcheckGPTClaimProcessorModel)
            if on_partial is None
            else await self._stream(messages, on_partial)
        )
        return [
            Claim(text=claim) for claim, label in zip(result.claims, result.checkworthy, strict=False) if label == "Yes"
        ]

    async def _stream(
        self, messages: list[Message], on_partial: Callable[[FactcheckGPTClaimProcessorModel], None]
    ) -> FactcheckGPTClaimProcessorModel:
        """Stream the extraction, forwarding each partial result to ``on_partial``."""
        result: FactcheckGPTClaimProcessorModel | None = None
        async for partial in self.client.astream_as(messages, FactcheckGPTClaimProcessorModel):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("claim processor stream produced no value")
        return result
