"""FactcheckGPT verifier."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.components.types import Claim, Evidence, Verdict
from openfactcheck.messages import Message
from openfactcheck.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class Verification(BaseModel):
    """FactcheckGPT's structured per-claim verification result.

    The verifier maps this onto a [`Verdict`][openfactcheck.components.types.Verdict].
    It is also the value handed to a verifier call's ``on_partial`` hook, filling
    in field by field as the model writes it.
    """

    reasoning: str
    factuality: bool
    error: str | None = None
    correction: str | None = None


@dataclass(frozen=True, slots=True)
class FactcheckGPTVerifier:
    """Judge a claim against its evidence, following FactcheckGPT's method.

    FactcheckGPT reports factuality as a boolean and, when the claim is wrong,
    the error and a correction. The boolean maps to ``supported`` or ``refuted``;
    FactcheckGPT emits no confidence, so the verdict leaves it unset.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "verifier.md"))
    """The verification prompt. Defaults to FactcheckGPT's; override to customise."""

    async def __call__(
        self,
        claim: Claim,
        evidence: Evidence,
        *,
        on_partial: Callable[[Verification], None] | None = None,
    ) -> Verdict:
        """Verify ``claim`` against ``evidence``.

        Args:
            claim: Claim under evaluation.
            evidence: Sources bearing on the claim's truthfulness.
            on_partial: Called with the verification result as it streams in, each
                call carrying the fields filled so far. Omit it for a single
                non-streaming call. The returned verdict is the same either way.

        Returns:
            A verdict labelled ``supported`` or ``refuted``, with the error and
            correction filled when the claim is judged non-factual.
        """
        messages = self.prompt.to_messages(claim=claim.text, evidence=self._format_evidence(evidence))
        result = (
            await self.client.acompletion_as(messages, Verification)
            if on_partial is None
            else await self._stream(messages, on_partial)
        )
        return Verdict(
            claim=claim,
            label="supported" if result.factuality else "refuted",
            confidence=None,
            reasoning=result.reasoning,
            error=self._clean(result.error),
            correction=self._clean(result.correction),
        )

    async def _stream(self, messages: list[Message], on_partial: Callable[[Verification], None]) -> Verification:
        """Stream the verification, forwarding each partial result to ``on_partial``."""
        result: Verification | None = None
        async for partial in self.client.astream_as(messages, Verification):
            result = partial
            on_partial(partial)
        if result is None:  # pragma: no cover - astream_as yields the final value or raises.
            raise RuntimeError("verifier stream produced no value")
        return result

    @staticmethod
    def _format_evidence(evidence: Evidence) -> str:
        """Render the evidence as a list of passage contents, as FactcheckGPT does."""
        return str([source.content for source in evidence.sources])

    @staticmethod
    def _clean(value: str | None) -> str | None:
        """Treat the literal string ``None`` or a blank string as no value."""
        if value is None or value.strip() in {"", "None"}:
            return None
        return value
