"""Tests for core data types."""

import pytest
from pydantic import ValidationError

from openfactcheck.components.types import (
    Claim,
    Evidence,
    Input,
    Query,
    Result,
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

    assert verdict.evidence is None
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


def test_result() -> None:
    claim = Claim(text="The earth is flat")
    evidence = Evidence(claim=claim, sources=[Source(content="Earth is a sphere")])
    verdict = Verdict(claim=claim, evidence=evidence, label="refuted", confidence=0.99, reasoning="Contradicted")

    result = Result(verdicts=[verdict])
    assert len(result.verdicts) == 1
    assert result.verdicts[0].label == "refuted"
    assert result.verdicts[0].evidence is not None
    assert result.verdicts[0].evidence.sources[0].content == "Earth is a sphere"
    assert result.revision is None
    assert result.attribution is None


def test_result_empty() -> None:
    result = Result(verdicts=[])
    assert result.verdicts == []


def test_result_carries_revision_and_attribution() -> None:
    sources = [Source(content="cited passage", metadata=WebMetadata(url="https://x.com"))]

    result = Result(
        verdicts=[],
        revision="The sky is blue",
        attribution=sources,
    )

    assert result.revision == "The sky is blue"
    assert result.attribution == sources


def test_serialization_round_trip() -> None:
    claim = Claim(text="Water is wet")
    source = Source(content="Scientific consensus", metadata=WebMetadata(url="https://x.com", title="X"))
    evidence = Evidence(claim=claim, sources=[source])
    verdict = Verdict(claim=claim, evidence=evidence, label="supported", confidence=0.9, reasoning="Well established")

    result = Result(verdicts=[verdict])

    data = result.model_dump()
    restored = Result.model_validate(data)
    assert restored.verdicts[0].label == "supported"
    assert restored.verdicts[0].evidence is not None
    restored_source = restored.verdicts[0].evidence.sources[0]
    assert restored_source.content == "Scientific consensus"
    assert isinstance(restored_source.metadata, WebMetadata)
    assert restored_source.metadata.url == "https://x.com"
    assert restored_source.metadata.title == "X"


def test_frozen_model_rejects_mutation() -> None:
    claim = Claim(text="The earth is round")

    with pytest.raises(ValidationError):
        claim.text = "mutated"
