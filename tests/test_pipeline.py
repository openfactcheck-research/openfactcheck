"""Tests for the default fact-check pipeline wired on the graph layer."""

import asyncio

from openfactcheck.pipeline import Components, PipelineState, build_pipeline
from openfactcheck.types import Claim, Evidence, Input, OverallVerdict, Source, Verdict


async def _process(text: Input) -> list[Claim]:
    return [Claim(text=sentence.strip()) for sentence in text.content.split(".") if sentence.strip()]


async def _retrieve(claim: Claim) -> Evidence:
    return Evidence(claim=claim, sources=[Source(content=f"evidence for {claim.text}")])


async def _verify(claim: Claim, evidence: Evidence) -> Verdict:
    label = "supported" if evidence.sources else "not_enough_evidence"
    return Verdict(claim=claim, label=label, confidence=0.9, reasoning="stub")


async def _aggregate(verdicts: list[Verdict]) -> OverallVerdict:
    if not verdicts:
        return OverallVerdict(label="not_enough_evidence", score=0.0)
    supported = sum(1 for verdict in verdicts if verdict.label == "supported")
    score = supported / len(verdicts)
    label = "supported" if score >= 0.5 else "refuted"  # noqa: PLR2004 - simple stub threshold.
    return OverallVerdict(label=label, score=score)


def test_build_pipeline_runs_end_to_end() -> None:
    components = Components(processor=_process, retriever=_retrieve, verifier=_verify, aggregator=_aggregate)

    result = build_pipeline().run(
        Input(content="The sky is blue. Water is wet."), state=PipelineState(), deps=components
    )

    assert [claim.text for claim in result.claims] == ["The sky is blue", "Water is wet"]
    assert all(verdict.label == "supported" for verdict in result.verdicts)
    assert result.overall_label == "supported"
    assert result.overall_score == 1.0
    # The result carries the real input and per-claim evidence, aligned by claim.
    assert result.input.content == "The sky is blue. Water is wet."
    assert len(result.evidence) == len(result.claims)
    assert [evidence.claim for evidence in result.evidence] == result.claims


def test_build_pipeline_preserves_claim_order() -> None:
    delays = {"a": 0.03, "b": 0.0, "c": 0.0}

    async def slow_retrieve(claim: Claim) -> Evidence:
        await asyncio.sleep(delays.get(claim.text, 0.0))
        return Evidence(claim=claim, sources=[Source(content=f"e:{claim.text}")])

    components = Components(processor=_process, retriever=slow_retrieve, verifier=_verify, aggregator=_aggregate)

    result = build_pipeline().run(Input(content="a. b. c."), state=PipelineState(), deps=components)

    # Source order survives nondeterministic branch completion.
    assert [claim.text for claim in result.claims] == ["a", "b", "c"]
    assert [verdict.claim.text for verdict in result.verdicts] == ["a", "b", "c"]
    assert [evidence.claim.text for evidence in result.evidence] == ["a", "b", "c"]


def test_build_pipeline_zero_claims() -> None:
    components = Components(processor=_process, retriever=_retrieve, verifier=_verify, aggregator=_aggregate)

    result = build_pipeline().run(Input(content="   "), state=PipelineState(), deps=components)

    assert result.claims == []
    assert result.evidence == []
    assert result.verdicts == []
    assert result.input.content == "   "
    assert result.overall_label == "not_enough_evidence"


def test_build_pipeline_duplicate_claims() -> None:
    components = Components(processor=_process, retriever=_retrieve, verifier=_verify, aggregator=_aggregate)

    result = build_pipeline().run(Input(content="dup. dup."), state=PipelineState(), deps=components)

    assert [claim.text for claim in result.claims] == ["dup", "dup"]
    assert len(result.verdicts) == 2


def test_build_pipeline_state_records_input() -> None:
    components = Components(processor=_process, retriever=_retrieve, verifier=_verify, aggregator=_aggregate)
    state = PipelineState()

    build_pipeline().run(Input(content="The sky is blue."), state=state, deps=components)

    assert state.input == Input(content="The sky is blue.")
