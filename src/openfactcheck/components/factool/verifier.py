"""Factool verifier."""

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from openfactcheck.chat import ChatClient
from openfactcheck.prompts import PromptTemplate
from openfactcheck.types import Claim, Evidence, Verdict

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class _Verification(BaseModel):
    """Structured output: Factool's per-claim verification result."""

    reasoning: str
    factuality: bool
    error: str | None = None
    correction: str | None = None


@dataclass(frozen=True, slots=True)
class FactoolVerifier:
    """Judge a claim against its evidence, following Factool's method.

    Factool reports factuality as a boolean and, when the claim is wrong, the
    error and a correction. The boolean maps to ``supported`` or ``refuted``;
    Factool emits no confidence, so the verdict leaves it unset.
    """

    client: ChatClient
    """The chat client used to call the model."""

    prompt: PromptTemplate = field(default_factory=lambda: PromptTemplate.from_file(_PROMPTS_DIR / "verifier.md"))
    """The verification prompt. Defaults to Factool's; override to customise."""

    async def __call__(self, claim: Claim, evidence: Evidence) -> Verdict:
        """Verify ``claim`` against ``evidence``.

        Args:
            claim: Claim under evaluation.
            evidence: Sources bearing on the claim's truthfulness.

        Returns:
            A verdict labelled ``supported`` or ``refuted``, with the error and
            correction filled when the claim is judged non-factual.
        """
        messages = self.prompt.to_messages(claim=claim.text, evidence=self._format_evidence(evidence))
        result = await self.client.acompletion_as(messages, _Verification)
        return Verdict(
            claim=claim,
            label="supported" if result.factuality else "refuted",
            confidence=None,
            reasoning=result.reasoning,
            error=self._clean(result.error),
            correction=self._clean(result.correction),
        )

    @staticmethod
    def _format_evidence(evidence: Evidence) -> str:
        """Render the evidence as a list of snippet contents, as Factool does."""
        return str([source.content for source in evidence.sources])

    @staticmethod
    def _clean(value: str | None) -> str | None:
        """Treat the literal string ``None`` or a blank string as no value."""
        if value is None or value.strip() in {"", "None"}:
            return None
        return value
