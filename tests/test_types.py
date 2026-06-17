"""Tests for core data types."""

import pytest
from pydantic import ValidationError

from openfactcheck.types import (
    Claim,
    ClaimReport,
    Evidence,
    FactCheckResult,
    Input,
    OverallVerdict,
    Query,
    Source,
    Verdict,
    WebMetadata,
)


def test_input() -> None:
    inp = Input(content="The earth is flat and water is wet")
    assert inp.content == "The earth is flat and water is wet"


def test_claim() -> None:
    claim = Claim(text="The earth is round")
    assert claim.text == "The earth is round"


def test_query() -> None:
    claim = Claim(text="Water boils at 100C")
    query = Query(claim=claim, questions=["At what temperature does water boil?"])
    assert query.claim.text == "Water boils at 100C"
    assert len(query.questions) == 1


def test_source_default_metadata() -> None:
    source = Source(content="Some evidence text")
    assert source.content == "Some evidence text"
    assert source.metadata is not None


def test_source_with_web_metadata() -> None:
    source = Source(
        content="NASA confirms earth is round",
        metadata=WebMetadata(url="https://nasa.gov", title="NASA"),
    )
    assert isinstance(source.metadata, WebMetadata)
    assert source.metadata.url == "https://nasa.gov"
    assert source.metadata.title == "NASA"


def test_web_metadata_title_defaults_to_none() -> None:
    metadata = WebMetadata(url="https://nasa.gov")
    assert metadata.title is None


def test_evidence() -> None:
    claim = Claim(text="The earth is round")
    evidence = Evidence(
        claim=claim,
        sources=[
            Source(content="Evidence 1", metadata=WebMetadata(url="https://a.com", title="A")),
            Source(content="Evidence 2", metadata=WebMetadata(url="https://b.com", title="B")),
        ],
    )
    assert evidence.claim.text == "The earth is round"
    assert len(evidence.sources) == 2


def test_verdict() -> None:
    claim = Claim(text="The earth is round")
    verdict = Verdict(
        claim=claim,
        label="supported",
        confidence=0.95,
        reasoning="Multiple sources confirm this.",
    )
    assert verdict.label == "supported"
    assert verdict.confidence == 0.95


def test_verdict_optional_fields_default_to_none() -> None:
    claim = Claim(text="The earth is round")
    verdict = Verdict(claim=claim, label="supported", reasoning="confirmed")

    assert verdict.confidence is None
    assert verdict.error is None
    assert verdict.correction is None


def test_verdict_carries_error_and_correction() -> None:
    claim = Claim(text="The earth is flat")
    verdict = Verdict(
        claim=claim,
        label="refuted",
        reasoning="Contradicted by evidence.",
        error="The earth is not flat.",
        correction="The earth is round.",
    )

    assert verdict.error == "The earth is not flat."
    assert verdict.correction == "The earth is round."


def test_fact_check_result() -> None:
    claim = Claim(text="The earth is flat")
    evidence = Evidence(claim=claim, sources=[Source(content="Earth is a sphere")])
    verdict = Verdict(claim=claim, label="refuted", confidence=0.99, reasoning="Contradicted by evidence")

    result = FactCheckResult(
        input=Input(content="The earth is flat"),
        claims=[claim],
        evidence=[evidence],
        verdicts=[verdict],
        overall_label="refuted",
        overall_score=0.01,
    )
    assert result.overall_label == "refuted"
    assert len(result.claims) == 1
    assert len(result.evidence) == 1
    assert len(result.verdicts) == 1


def test_fact_check_result_empty() -> None:
    result = FactCheckResult(
        input=Input(content=""),
        claims=[],
        evidence=[],
        verdicts=[],
        overall_label="not_enough_evidence",
        overall_score=0.0,
    )
    assert result.claims == []
    assert result.verdicts == []


def test_serialization_round_trip() -> None:
    claim = Claim(text="Water is wet")
    source = Source(content="Scientific consensus", metadata=WebMetadata(url="https://x.com", title="X"))
    evidence = Evidence(claim=claim, sources=[source])
    verdict = Verdict(claim=claim, label="supported", confidence=0.9, reasoning="Well established fact")

    result = FactCheckResult(
        input=Input(content="Water is wet"),
        claims=[claim],
        evidence=[evidence],
        verdicts=[verdict],
        overall_label="supported",
        overall_score=0.9,
    )

    data = result.model_dump()
    restored = FactCheckResult.model_validate(data)
    assert restored.verdicts[0].label == "supported"
    assert restored.evidence[0].sources[0].content == "Scientific consensus"


def test_overall_verdict() -> None:
    overall = OverallVerdict(label="supported", score=0.8)
    assert overall.label == "supported"
    assert overall.score == 0.8


def test_claim_report() -> None:
    claim = Claim(text="The earth is round")
    evidence = Evidence(claim=claim, sources=[Source(content="NASA")])
    verdict = Verdict(claim=claim, label="supported", confidence=0.9, reasoning="confirmed")

    report = ClaimReport(claim=claim, evidence=evidence, verdict=verdict)

    assert report.claim == claim
    assert report.evidence == evidence
    assert report.verdict.label == "supported"


def test_frozen_model_rejects_mutation() -> None:
    claim = Claim(text="The earth is round")

    with pytest.raises(ValidationError):
        claim.text = "mutated"
