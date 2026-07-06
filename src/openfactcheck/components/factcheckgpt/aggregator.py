"""FactcheckGPT aggregator."""

from collections.abc import Callable
from dataclasses import dataclass

from openfactcheck.components.types import Result, Verdict


@dataclass(frozen=True, slots=True)
class FactcheckGPTAggregator:
    """Aggregator that gathers FactcheckGPT's per-claim verdicts into a result.

    Wraps the verdicts in a [`Result`][Result] and lets it compute the summary,
    making no model calls.
    """

    async def __call__(
        self,
        verdicts: list[Verdict],
        *,
        on_partial: Callable[[object], None] | None = None,
    ) -> Result:
        """Gather ``verdicts`` into a result.

        Args:
            verdicts: The per-claim verdicts to consolidate.
            on_partial: Ignored; this component produces its result in one step.

        Returns:
            A result carrying the verdicts, with the summary computed from them.
        """
        return Result(verdicts=verdicts)
