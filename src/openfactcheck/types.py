"""Core data types for the fact-checking pipeline."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Input(BaseModel):
    """Content to be fact-checked."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    content: str
    """The text to be fact-checked."""


class Claim(BaseModel):
    """A single factual claim extracted from the input."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    text: str
    """The factual statement being checked."""


class Query(BaseModel):
    """Search queries generated for verifying a claim."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    claim: Claim
    """The claim the queries seek evidence for."""

    questions: list[str]
    """Search questions derived from the claim."""


class SourceMetadata(BaseModel):
    """Base metadata for a source. Subclass for specific source types."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)


class WebMetadata(SourceMetadata):
    """Metadata for a web source."""

    url: str
    """Address of the web page."""

    title: str | None = None
    """Title of the web page, or ``None`` when the source provides none."""


class Source(BaseModel):
    """A piece of evidence from any source type."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    content: str
    """The source's textual content."""

    metadata: SourceMetadata = SourceMetadata()
    """Structured metadata describing where the source came from."""


class Evidence(BaseModel):
    """Evidence collected for a single claim."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    claim: Claim
    """The claim this evidence bears on."""

    sources: list[Source]
    """Sources gathered for the claim; empty when nothing was found."""


class Verdict(BaseModel):
    """Verification result for a single claim."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    claim: Claim
    """The claim being judged."""

    label: Literal["supported", "refuted", "not_enough_evidence"]
    """Whether the evidence supports, refutes, or is insufficient for the claim."""

    confidence: float | None = None
    """How strongly the evidence backs the assigned label, or ``None`` when the verifier reports no confidence."""

    reasoning: str
    """Explanation for the assigned label."""

    error: str | None = None
    """The factual error found in the claim, or ``None`` when the claim is accurate or the verifier finds no error."""

    correction: str | None = None
    """A corrected version of the claim, or ``None`` when there is nothing to correct."""


class OverallVerdict(BaseModel):
    """Aggregate judgment over a run's per-claim verdicts."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    label: str
    """Overall outcome label for the run, named by the aggregation strategy."""

    score: float
    """Overall confidence or agreement score for the run."""


class ClaimReport(BaseModel):
    """A single claim paired with its evidence and verdict.

    Keeps the per-claim artifacts produced across the pipeline aligned, so the
    overall result can be assembled from a list of reports in claim order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    claim: Claim
    """The claim this report concerns."""

    evidence: Evidence
    """Evidence gathered for the claim."""

    verdict: Verdict
    """Verdict reached for the claim against its evidence."""


class FactCheckResult(BaseModel):
    """Complete result of a fact-checking pipeline run."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    input: Input
    """The original input that was checked."""

    claims: list[Claim]
    """Claims extracted from the input."""

    evidence: list[Evidence]
    """Evidence gathered for each claim."""

    verdicts: list[Verdict]
    """Per-claim verdicts."""

    overall_label: str
    """Aggregate outcome label for the whole input."""

    overall_score: float
    """Aggregate confidence or agreement score for the whole input."""
