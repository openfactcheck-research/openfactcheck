"""Core data types for fact-checking.

The vocabulary that flows between components, the per-claim record the pipeline
collects, and the assembled run result. Each category contract is defined in
terms of these types, so any implementation of one category produces what the
next can take.
"""

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
    """Verification result for a single claim: the judgment and the evidence behind it."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    claim: Claim
    """The claim being judged."""

    evidence: Evidence | None = None
    """Evidence weighed in reaching the verdict, or ``None`` when the claim was judged without retrieval."""

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


class Assessment(BaseModel):
    """The overall judgment for a fact-checked input."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    label: str
    """Overall outcome label, named by the aggregation strategy."""


class Report(BaseModel):
    """The complete result of fact-checking an input."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    input: Input
    """The original input that was checked."""

    verdicts: list[Verdict]
    """The verdict for each extracted claim, each carrying its claim and the evidence behind it."""

    assessment: Assessment
    """The overall judgment across all claims."""

    revision: str | None = None
    """The input rewritten to correct its factual errors, or ``None`` when no revision was produced."""

    attribution: list[Source] | None = None
    """Sources cited as the attribution report for the result, or ``None`` when the pipeline produces none."""
