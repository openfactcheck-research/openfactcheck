"""Factool aggregator."""

from dataclasses import dataclass

from openfactcheck.components.types import Assessment, Verdict


@dataclass(frozen=True, slots=True)
class FactoolAggregator:
    """Combine per-claim verdicts with Factool's response-level rule.

    A response is factual only when every claim is supported; a single
    unsupported claim makes the whole response non-factual.
    """

    async def __call__(self, verdicts: list[Verdict]) -> Assessment:
        """Aggregate per-claim verdicts into one overall judgment.

        Args:
            verdicts: Per-claim verdicts; may be empty.

        Returns:
            An overall judgment labelled ``factual`` or ``non_factual``, or
            ``not_enough_evidence`` when there are no verdicts.
        """
        if not verdicts:
            return Assessment(label="not_enough_evidence")
        factual = all(verdict.label == "supported" for verdict in verdicts)
        return Assessment(label="factual" if factual else "non_factual")
