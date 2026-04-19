"""Component category contracts for the fact-checking pipeline.

Each component category is a ``Protocol`` defining the signature any
implementation must match. Paper-specific components (Factool, RARR, and
so on) live in separate modules under ``openfactcheck.components`` and
are interchangeable with any other implementation of the same category.
"""

from typing import Protocol, runtime_checkable

from openfactcheck.types import Claim, Evidence, FactCheckResult, Input, Query, Verdict


@runtime_checkable
class ClaimExtractor(Protocol):
    """Extract atomic factual claims from input text.

    One input may yield zero or more claims. Returning an empty list is
    valid (for example, when the input contains no checkable claims).
    """

    async def __call__(self, text: Input) -> list[Claim]:
        """Extract claims from ``text``.

        Args:
            text: Raw input text to scan for claims.

        Returns:
            Atomic factual claims found in ``text``; empty when there are
            no checkable claims.
        """
        ...


@runtime_checkable
class QueryGenerator(Protocol):
    """Generate search queries for a claim.

    Optional category. Some pipelines separate query generation from
    retrieval; others bundle both inside a ``Retriever``. The default
    library pipeline bundles them.
    """

    async def __call__(self, claim: Claim) -> Query:
        """Generate a query for ``claim``.

        Args:
            claim: Claim to fetch evidence for.

        Returns:
            Search query derived from the claim.
        """
        ...


@runtime_checkable
class Retriever(Protocol):
    """Fetch evidence for a single claim.

    Evidence is a set of sources bearing on the claim's truthfulness:
    web pages, documents, vector-store results. A retriever that finds
    nothing should return ``Evidence(claim=claim, sources=[])``.
    """

    async def __call__(self, claim: Claim) -> Evidence:
        """Fetch evidence for ``claim``.

        Args:
            claim: Claim to gather evidence for.

        Returns:
            Evidence attached to ``claim``; may contain an empty
            ``sources`` list when nothing was found.
        """
        ...


@runtime_checkable
class Verifier(Protocol):
    """Decide whether evidence supports, refutes, or is insufficient for a claim."""

    async def __call__(self, claim: Claim, evidence: Evidence) -> Verdict:
        """Verify ``claim`` against ``evidence``.

        Args:
            claim: Claim under evaluation.
            evidence: Sources bearing on the claim's truthfulness.

        Returns:
            Verdict describing whether the evidence supports, refutes, or
            is insufficient for the claim.
        """
        ...


@runtime_checkable
class Aggregator(Protocol):
    """Combine per-claim verdicts into the pipeline's overall result.

    Implementations set ``overall_label`` and ``overall_score`` on the
    result. Strategy is implementation-defined (majority vote, weighted
    average, worst-case, and so on).
    """

    async def __call__(self, verdicts: list[Verdict]) -> FactCheckResult:
        """Aggregate per-claim verdicts.

        Args:
            verdicts: Per-claim verdicts produced earlier in the pipeline.

        Returns:
            Overall fact-check result with an aggregate label and score
            populated from ``verdicts``.
        """
        ...
