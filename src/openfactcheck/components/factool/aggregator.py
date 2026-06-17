"""Factool aggregator."""

from dataclasses import dataclass

from openfactcheck.types import OverallVerdict, Verdict


@dataclass(frozen=True, slots=True)
class FactoolAggregator:
    """Combine per-claim verdicts with Factool's response-level rule.

    A response is factual only when every claim is supported; a single
    unsupported claim makes the whole response non-factual. The score reports
    the fraction of supported claims.
    """

    async def __call__(self, verdicts: list[Verdict]) -> OverallVerdict:
        """Aggregate per-claim verdicts into one overall judgment.

        Args:
            verdicts: Per-claim verdicts; may be empty.

        Returns:
            An overall judgment labelled ``factual`` or ``non_factual``, or
            ``not_enough_evidence`` when there are no verdicts.
        """
        if not verdicts:
            return OverallVerdict(label="not_enough_evidence", score=0.0)
        supported = sum(1 for verdict in verdicts if verdict.label == "supported")
        label = "factual" if supported == len(verdicts) else "non_factual"
        return OverallVerdict(label=label, score=supported / len(verdicts))
