"""Component category contracts for the fact-checking pipeline.

Each component category is a ``Protocol`` defining the signature any
implementation must match. Implementations live in sibling subpackages
(``dummy``, ``default``, and paper ports such as ``factool``) and are
interchangeable with any other implementation of the same category.
"""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from openfactcheck.components.types import Assessment, Claim, Evidence, Input, Query, Verdict


@runtime_checkable
class ClaimProcessor(Protocol):
    """Turn input text into atomic factual claims.

    One input may yield zero or more claims. Returning an empty list is
    valid (for example, when the input contains no checkable claims).
    """

    async def __call__(self, text: Input, *, on_partial: Callable[[object], None] | None = None) -> list[Claim]:
        """Produce atomic claims from ``text``.

        Args:
            text: Input text to process into claims.
            on_partial: Optional sink called with the in-progress result as it
                streams in, each call carrying more of it. Omit it for a single
                non-streaming call; an implementation without streaming may
                ignore it.

        Returns:
            Atomic factual claims drawn from ``text``; empty when there are
            no checkable claims.
        """
        ...


@runtime_checkable
class QueryGenerator(Protocol):
    """Generate search queries for a claim.

    Produces the search questions a [`Retriever`][Retriever] runs to gather
    evidence. One claim yields one [`Query`][openfactcheck.components.types.Query] holding
    any number of questions.
    """

    async def __call__(self, claim: Claim, *, on_partial: Callable[[object], None] | None = None) -> Query:
        """Generate a query for ``claim``.

        Args:
            claim: Claim to fetch evidence for.
            on_partial: Optional sink called with the in-progress result as it
                streams in, each call carrying more of it. Omit it for a single
                non-streaming call; an implementation without streaming may
                ignore it.

        Returns:
            Search query derived from the claim.
        """
        ...


@runtime_checkable
class Retriever(Protocol):
    """Fetch evidence for a claim's queries.

    A [`Query`][openfactcheck.components.types.Query] carries both the claim and the
    search questions generated for it. Evidence is a set of sources bearing on
    the claim's truthfulness: web pages, documents, vector-store results. A
    retriever that finds nothing should return
    ``Evidence(claim=query.claim, sources=[])``.
    """

    async def __call__(self, query: Query) -> Evidence:
        """Fetch evidence for ``query``.

        Args:
            query: The claim paired with the search questions to run.

        Returns:
            Evidence attached to the query's claim; may contain an empty
            ``sources`` list when nothing was found.
        """
        ...


@runtime_checkable
class Verifier(Protocol):
    """Decide whether evidence supports, refutes, or is insufficient for a claim."""

    async def __call__(
        self, claim: Claim, evidence: Evidence, *, on_partial: Callable[[object], None] | None = None
    ) -> Verdict:
        """Verify ``claim`` against ``evidence``.

        Args:
            claim: Claim under evaluation.
            evidence: Sources bearing on the claim's truthfulness.
            on_partial: Optional sink called with the in-progress result as it
                streams in, each call carrying more of it. Omit it for a single
                non-streaming call; an implementation without streaming may
                ignore it.

        Returns:
            Verdict describing whether the evidence supports, refutes, or
            is insufficient for the claim.
        """
        ...


@runtime_checkable
class Aggregator(Protocol):
    """Combine per-claim verdicts into one overall judgment.

    Strategy is implementation-defined (majority vote, weighted average,
    worst-case, and so on). The pipeline assembles the full result around
    the returned judgment.
    """

    async def __call__(self, verdicts: list[Verdict]) -> Assessment:
        """Aggregate per-claim verdicts into one overall judgment.

        Args:
            verdicts: Per-claim verdicts produced earlier in the pipeline;
                may be empty when the input yielded no claims.

        Returns:
            The overall judgment, with a strategy-defined label and score.
        """
        ...


@runtime_checkable
class Reviser(Protocol):
    """Rewrite input text to correct the factual errors its verdicts found.

    An optional final stage: most pipelines stop at the
    [`Verdict`][openfactcheck.components.types.Verdict] for each claim. A reviser
    weaves the per-claim corrections back into the original text, producing a
    revised version that preserves the wording and style of what was checked.
    """

    async def __call__(
        self, text: Input, verdicts: list[Verdict], *, on_partial: Callable[[object], None] | None = None
    ) -> str:
        """Rewrite ``text`` to fix the errors recorded in ``verdicts``.

        Args:
            text: The original input that was checked.
            verdicts: Per-claim verdicts, carrying the corrections to apply.
            on_partial: Optional sink called with the in-progress result as it
                streams in, each call carrying more of it. Omit it for a single
                non-streaming call; an implementation without streaming may
                ignore it.

        Returns:
            The input rewritten so its claims read as factually correct, with
            the original style preserved.
        """
        ...
