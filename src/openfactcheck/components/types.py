"""Core data types for fact-checking.

The vocabulary that flows between components, the per-claim record the pipeline
collects, and the assembled run result. Each category contract is defined in
terms of these types, so any implementation of one category produces what the
next can take.
"""

from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


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
    """Metadata for a source with no specific provenance. Subclass for specific source types."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    kind: Literal["none"] = "none"
    """Tag identifying the metadata type."""


class WebMetadata(SourceMetadata):
    """Metadata for a web source."""

    kind: Literal["web"] = "web"  # pyright: ignore[reportIncompatibleVariableOverride] - narrowing the discriminator is the point.
    """Tag identifying the metadata type."""

    url: str
    """Address of the web page."""

    title: str | None = None
    """Title of the web page, or ``None`` when the source provides none."""


type AnySourceMetadata = Annotated[SourceMetadata | WebMetadata, Field(discriminator="kind")]
"""Any source metadata, resolved to the concrete type by its ``kind`` tag."""


class Source(BaseModel):
    """A piece of evidence from any source type."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    content: str
    """The source's textual content."""

    metadata: AnySourceMetadata = SourceMetadata()
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


class ResultSummary(BaseModel):
    """Counts of a result's verdicts and an overall read of its factuality."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    supported: int
    """How many claims the evidence supported."""

    refuted: int
    """How many claims the evidence refuted."""

    not_enough_evidence: int
    """How many claims lacked sufficient evidence to judge."""

    total: int
    """How many claims were judged in total."""

    factual: bool | None
    """Whether the input reads as factual overall.

    ``True`` when every claim was supported, ``False`` when any claim was refuted, and ``None`` when no
    refutation was found but some claim lacked enough evidence (or there were no claims), so no overall
    judgment can be drawn.
    """


class Result(BaseModel):
    """The consolidated result of a fact-checking run: the verdicts and an overall read of them."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    verdicts: list[Verdict]
    """The verdict for each checked claim, each carrying its claim and the evidence behind it."""

    revision: str | None = None
    """The input revised to correct its factual errors, or ``None`` when no revision was produced."""

    attribution: list[Source] | None = None
    """Sources cited as attribution for the result, or ``None`` when the pipeline produces none."""

    @model_validator(mode="before")
    @classmethod
    def _drop_computed_summary(cls, data: object) -> object:
        """Ignore a serialized ``summary`` on input so a dumped result can be reloaded.

        The summary is computed from the verdicts, so it is recomputed rather than read back.
        """
        if isinstance(data, dict):
            mapping = cast("dict[str, object]", data)
            return {key: value for key, value in mapping.items() if key != "summary"}
        return data

    @computed_field
    @property
    def summary(self) -> ResultSummary:
        """Counts of the verdicts by label, with an overall factuality read."""
        supported = sum(verdict.label == "supported" for verdict in self.verdicts)
        refuted = sum(verdict.label == "refuted" for verdict in self.verdicts)
        not_enough_evidence = sum(verdict.label == "not_enough_evidence" for verdict in self.verdicts)
        total = len(self.verdicts)
        if refuted:
            factual = False
        elif total > 0 and supported == total:
            factual = True
        else:
            factual = None
        return ResultSummary(
            supported=supported,
            refuted=refuted,
            not_enough_evidence=not_enough_evidence,
            total=total,
            factual=factual,
        )
