"""RARR reviser: the agreement-gate-and-edit loop body, and the research state it threads."""

from collections.abc import Callable
from dataclasses import dataclass

from openfactcheck.components.rarr.agreement_gate import RARRAgreementGate
from openfactcheck.components.rarr.editor import RARREditor
from openfactcheck.components.rarr.retriever import QuestionedSource
from openfactcheck.components.types import Verdict


@dataclass(frozen=True, slots=True)
class RARRResearch:
    """The working state of RARR's research-and-revise loop: the passage, the evidence left, and the checks so far."""

    passage: str
    """The passage as edited so far."""

    pending: tuple[QuestionedSource, ...]
    """The ``(question, evidence)`` pairs still to check; empty once the loop has finished."""

    gates: tuple[Verdict, ...]
    """The agreement check recorded for each processed pair, in order."""


@dataclass(frozen=True, slots=True)
class RARRReviser:
    """Check the passage against its next piece of evidence and edit it to agree when it disagrees.

    One lap of RARR's revision loop: it takes the next ``(question, evidence)`` pair off the research state,
    checks the current passage against it with the agreement gate, edits the passage to agree on a
    disagreement, and records the check. Run it in a loop until no pairs remain, so each lap sees the passage as
    edited so far.
    """

    gate: RARRAgreementGate
    """The agreement gate that checks the passage against a piece of evidence."""

    editor: RARREditor
    """The editor that rewrites the passage to agree with evidence it contradicts."""

    async def __call__(
        self,
        research: RARRResearch,
        *,
        on_partial: Callable[[object], None] | None = None,
    ) -> RARRResearch:
        """Check and revise the passage against the next pending pair.

        Args:
            research: The current research state; its first pending pair is processed.
            on_partial: Optional sink called with the in-progress gate or edit as it streams in.

        Returns:
            The research state advanced by one pair: the passage as edited, that pair dropped from pending, and
            its agreement check appended.
        """
        question, source = research.pending[0]
        verdict = await self.gate(research.passage, question, source, on_partial=on_partial)
        passage = (
            await self.editor(research.passage, question, source, on_partial=on_partial)
            if verdict.label == "refuted"
            else research.passage
        )
        return RARRResearch(passage=passage, pending=research.pending[1:], gates=(*research.gates, verdict))
