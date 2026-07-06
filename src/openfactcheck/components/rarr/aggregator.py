"""RARR aggregator."""

from collections.abc import Callable
from dataclasses import dataclass

from openfactcheck.components.rarr.reviser import RARRResearch
from openfactcheck.components.types import Result


@dataclass(frozen=True, slots=True)
class RARRAggregator:
    """Aggregator that consolidates RARR's research state into a result.

    Puts the per-pair agreement checks into the result's verdicts and the revised passage into its revision,
    making no model calls.
    """

    async def __call__(
        self,
        research: RARRResearch,
        *,
        on_partial: Callable[[object], None] | None = None,
    ) -> Result:
        """Consolidate ``research`` into a result.

        Args:
            research: The finished research state, carrying the revised passage and its agreement checks.
            on_partial: Ignored; this component produces its result in one step.

        Returns:
            A result whose verdicts are the agreement checks and whose revision is the edited passage.
        """
        return Result(verdicts=list(research.gates), revision=research.passage)
