"""RARR agreement gate."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Claim, Evidence, Source, Verdict
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

_LABELS: dict[str, Literal["supported", "refuted", "not_enough_evidence"]] = {
    "agrees": "supported",
    "disagrees": "refuted",
    "irrelevant": "not_enough_evidence",
}
"""Maps RARR's three agreement outcomes onto the canonical verdict labels."""


class RARRAgreementGateModel(BaseModel):
    """RARR's structured agreement-gate result.

    The gate maps this onto a [`Verdict`][Verdict],
    where ``disagrees`` opens the gate for editing. It is also the value handed to
    a call's ``on_partial`` hook, filling in as the model writes it.
    """

    reasoning: str
    decision: Literal["agrees", "disagrees", "irrelevant"]


@dataclass(frozen=True, slots=True)
class RARRAgreementGate:
    """Decide whether a passage agrees with a piece of evidence, following RARR's method.

    Given the passage so far, a question, and the evidence found for it, the gate
    reasons about the answer each implies and decides whether they agree,
    disagree, or whether the evidence is irrelevant. A ``disagrees`` verdict
    (mapped to ``refuted``) opens the gate, signalling the passage should be
    edited.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "agreement_gate.md"))
    """The agreement-gate prompt. Defaults to RARR's; override to customise."""

    async def __call__(
        self,
        passage: str,
        question: str,
        source: Source,
        *,
        on_partial: Callable[[RARRAgreementGateModel], None] | None = None,
    ) -> Verdict:
        """Check whether ``passage`` agrees with ``source`` on the answer to ``question``.

        Args:
            passage: The passage as edited so far.
            question: The question the evidence was retrieved for.
            source: The evidence to check the passage against.
            on_partial: Called with the agreement result as it streams in. Omit it
                for a single non-streaming call. The returned verdict is the same
                either way.

        Returns:
            A verdict labelled ``supported`` (agrees), ``refuted`` (disagrees), or
            ``not_enough_evidence`` (irrelevant), carrying the gate's reasoning and
            the evidence it weighed.
        """
        messages = self.prompt.to_messages(claim=passage, query=question, evidence=source.content)
        result = (
            await self.client.acompletion_as(messages, RARRAgreementGateModel)
            if on_partial is None
            else await self._stream(messages, on_partial)
        )
        claim = Claim(text=passage)
        return Verdict(
            claim=claim,
            evidence=Evidence(claim=claim, sources=[source]),
            label=_LABELS[result.decision],
            reasoning=result.reasoning,
        )

    async def _stream(
        self, messages: list[Message], on_partial: Callable[[RARRAgreementGateModel], None]
    ) -> RARRAgreementGateModel:
        """Stream the agreement check, forwarding each partial result to ``on_partial``."""
        result: RARRAgreementGateModel | None = None
        async for partial in self.client.astream_as(messages, RARRAgreementGateModel):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("agreement gate stream produced no value")
        return result
