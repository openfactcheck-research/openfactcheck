"""Dummy aggregator."""

from dataclasses import dataclass

from openfactcheck.components.types import Assessment, Verdict


@dataclass(frozen=True, slots=True)
class DummyAggregator:
    """Aggregator that reaches no overall judgment.

    Returns a fixed inconclusive judgment, ignoring the per-claim verdicts.
    """

    async def __call__(self, verdicts: list[Verdict]) -> Assessment:
        """Return a fixed inconclusive judgment.

        Args:
            verdicts: Per-claim verdicts; ignored.

        Returns:
            An overall judgment labelled ``not_enough_evidence``.
        """
        return Assessment(label="not_enough_evidence")
