"""Component category contracts for the fact-checking pipeline.

Each component category is a ``Protocol`` defining the signature that any
implementation must match. Paper-specific components (Factool, RARR, ...) live
in separate modules under ``openfactcheck.components`` and are interchangeable
with any other implementation of the same category.

See :doc:`/docs/PHILOSOPHY` for the design rationale — in short, typed
contracts replace v1's stringly-typed state-dict passing.
"""

from typing import Protocol, runtime_checkable

from openfactcheck.types import Claim, Evidence, FactCheckResult, Input, Query, Verdict


@runtime_checkable
class ClaimExtractor(Protocol):
    """Extract atomic factual claims from input text.

    One input may yield zero or more claims. Returning an empty list is
    valid (e.g. the input contains no checkable claims).
    """

    async def __call__(self, text: Input) -> list[Claim]: ...


@runtime_checkable
class QueryGenerator(Protocol):
    """Generate search queries for a claim.

    Optional category. Some pipelines separate query generation from
    retrieval; others bundle both inside a ``Retriever``. The default
    library pipeline bundles them.
    """

    async def __call__(self, claim: Claim) -> Query: ...


@runtime_checkable
class Retriever(Protocol):
    """Fetch evidence for a single claim.

    Evidence is a set of sources bearing on the claim's truthfulness —
    web pages, documents, vector-store results. A retriever that finds
    nothing should return ``Evidence(claim=claim, sources=[])``.
    """

    async def __call__(self, claim: Claim) -> Evidence: ...


@runtime_checkable
class Verifier(Protocol):
    """Decide whether evidence supports, refutes, or is insufficient for a claim."""

    async def __call__(self, claim: Claim, evidence: Evidence) -> Verdict: ...


@runtime_checkable
class Aggregator(Protocol):
    """Combine per-claim verdicts into the pipeline's overall result.

    Implementations set ``overall_label`` and ``overall_score`` on the
    result. Strategy is implementation-defined (majority vote, weighted
    average, worst-case, etc.).
    """

    async def __call__(self, verdicts: list[Verdict]) -> FactCheckResult: ...
