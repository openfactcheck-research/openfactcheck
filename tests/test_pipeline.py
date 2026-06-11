"""Tests for the default fact-check pipeline wired on the graph layer."""

from openfactcheck.pipeline import Components, build_pipeline
from openfactcheck.types import (
    Claim,
    Evidence,
    FactCheckResult,
    Input,
    Source,
    Verdict,
)


async def _extract(text: Input) -> list[Claim]:
    return [Claim(text=sentence) for sentence in text.content.split(".") if sentence.strip()]


async def _retrieve(claim: Claim) -> Evidence:
    return Evidence(claim=claim, sources=[Source(content=f"evidence for {claim.text}")])


async def _verify(claim: Claim, evidence: Evidence) -> Verdict:
    label = "supported" if evidence.sources else "not_enough_evidence"
    return Verdict(claim=claim, label=label, confidence=0.9, reasoning="stub")


async def _aggregate(verdicts: list[Verdict]) -> FactCheckResult:
    supported = sum(1 for verdict in verdicts if verdict.label == "supported")
    score = supported / len(verdicts) if verdicts else 0.0
    return FactCheckResult(
        input=Input(content=""),
        claims=[verdict.claim for verdict in verdicts],
        evidence=[],
        verdicts=verdicts,
        overall_label="supported" if score >= 0.5 else "refuted",  # noqa: PLR2004 - simple stub threshold.
        overall_score=score,
    )


def test_build_pipeline_runs_end_to_end() -> None:
    graph = build_pipeline()
    components = Components(extractor=_extract, retriever=_retrieve, verifier=_verify, aggregator=_aggregate)

    result = graph.run(Input(content="The sky is blue. Water is wet."), state=None, deps=components)

    assert [claim.text.strip() for claim in result.claims] == ["The sky is blue", "Water is wet"]
    assert all(verdict.label == "supported" for verdict in result.verdicts)
    assert result.overall_label == "supported"
    assert result.overall_score == 1.0
