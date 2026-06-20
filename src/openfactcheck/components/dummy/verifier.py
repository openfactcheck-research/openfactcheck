"""Dummy verifier."""

from collections.abc import Callable
from dataclasses import dataclass

from openfactcheck.components.types import Claim, Evidence, Verdict


@dataclass(frozen=True, slots=True)
class DummyVerifier:
    """Verifier that reaches no conclusion.

    Returns a fixed inconclusive verdict for any claim, ignoring the evidence.
    """

    async def __call__(
        self,
        claim: Claim,
        evidence: Evidence,
        *,
        on_partial: Callable[[object], None] | None = None,
    ) -> Verdict:
        """Return a fixed inconclusive verdict for ``claim``.

        Args:
            claim: Claim under evaluation.
            evidence: Sources bearing on the claim; ignored.
            on_partial: Ignored; this component produces its result in one step.

        Returns:
            A verdict labelled ``not_enough_evidence`` with zero confidence.
        """
        return Verdict(
            claim=claim,
            label="not_enough_evidence",
            confidence=0.0,
            reasoning="No verification performed.",
        )
