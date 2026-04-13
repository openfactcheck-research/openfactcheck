"""Core data types for the fact-checking pipeline."""

from typing import Literal

from pydantic import BaseModel


class Input(BaseModel):
    """Content to be fact-checked."""

    content: str


class Claim(BaseModel):
    """A single factual claim extracted from the input."""

    text: str


class Query(BaseModel):
    """Search queries generated for verifying a claim."""

    claim: Claim
    questions: list[str]


class SourceMetadata(BaseModel):
    """Base metadata for a source. Subclass for specific source types."""


class WebMetadata(SourceMetadata):
    """Metadata for a web source."""

    url: str
    title: str


class Source(BaseModel):
    """A piece of evidence from any source type."""

    content: str
    metadata: SourceMetadata = SourceMetadata()


class Evidence(BaseModel):
    """Evidence collected for a single claim."""

    claim: Claim
    sources: list[Source]


class Verdict(BaseModel):
    """Verification result for a single claim."""

    claim: Claim
    label: Literal["supported", "refuted", "not_enough_evidence"]
    confidence: float
    reasoning: str


class FactCheckResult(BaseModel):
    """Complete result of a fact-checking pipeline run."""

    input: Input
    claims: list[Claim]
    evidence: list[Evidence]
    verdicts: list[Verdict]
    overall_label: str
    overall_score: float
