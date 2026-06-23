"""Factool claim processor."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Claim, Input
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class FactoolClaimProcessorModel(BaseModel):
    """Factool's structured claim-extraction result.

    The claim processor maps this onto a list of
    [`Claim`][Claim]. It is also the value handed to a call's
    ``on_partial`` hook, the claim list growing as the model writes it.
    """

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

    async def __call__(
        self,
        text: Input,
        *,
        on_partial: Callable[[FactoolClaimProcessorModel], None] | None = None,
    ) -> list[Claim]:
        """Extract atomic claims from ``text``.

        Args:
            text: Input text to process into claims.
            on_partial: Called with the extraction as it streams in, each call
                carrying the claims found so far. Omit it for a single
                non-streaming call. The returned claims are the same either way.

        Returns:
            The extracted claims; empty when the model finds none.
        """
        messages = self.prompt.to_messages(input=text.content)
        result = (
            await self.client.acompletion_as(messages, FactoolClaimProcessorModel)
            if on_partial is None
            else await self._stream(messages, on_partial)
        )
        return [Claim(text=claim) for claim in result.claims]

    async def _stream(
        self, messages: list[Message], on_partial: Callable[[FactoolClaimProcessorModel], None]
    ) -> FactoolClaimProcessorModel:
        """Stream the extraction, forwarding each partial result to ``on_partial``."""
        result: FactoolClaimProcessorModel | None = None
        async for partial in self.client.astream_as(messages, FactoolClaimProcessorModel):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("claim processor stream produced no value")
        return result
