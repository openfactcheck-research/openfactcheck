"""RARR aggregator."""

from dataclasses import dataclass

from openfactcheck.components.types import Assessment, Verdict


@dataclass(frozen=True, slots=True)
class RARRAggregator:
    """Summarize the revision run from its agreement checks, following RARR's spirit.

    RARR's goal is to revise a passage to agree with the evidence, not to assign
    an overall factual label. The label is ``unchanged`` when every check agreed
    (nothing needed editing) or ``revised`` when at least one disagreed.
    """

    async def __call__(self, verdicts: list[Verdict]) -> Assessment:
        """Summarize the agreement checks into one overall judgment.

        Args:
            verdicts: The per-question agreement checks; may be empty.

        Returns:
            An overall judgment labelled ``unchanged`` or ``revised``, or
            ``not_enough_evidence`` when there are no checks.
        """
        if not verdicts:
            return Assessment(label="not_enough_evidence")
        unchanged = all(verdict.label == "supported" for verdict in verdicts)
        return Assessment(label="unchanged" if unchanged else "revised")
