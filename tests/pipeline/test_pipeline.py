"""Tests for the fact-check pipeline and its default graph."""

import asyncio

from openfactcheck.components.dummy import (
    DummyAggregator,
    DummyClaimProcessor,
    DummyQueryGenerator,
    DummyRetriever,
    DummyVerifier,
)
from openfactcheck.components.protocols import Retriever
from openfactcheck.components.types import Assessment, Claim, Evidence, Input, Query, Source, Verdict
from openfactcheck.pipeline import Components, Pipeline, PipelineState, build_graph


async def _process(text: Input) -> list[Claim]:
    return [Claim(text=sentence.strip()) for sentence in text.content.split(".") if sentence.strip()]


async def _generate(claim: Claim) -> Query:
    return Query(claim=claim, questions=[f"is '{claim.text}' true?"])


async def _retrieve(query: Query) -> Evidence:
    return Evidence(claim=query.claim, sources=[Source(content=f"evidence for {query.claim.text}")])


async def _verify(claim: Claim, evidence: Evidence) -> Verdict:
    label = "supported" if evidence.sources else "not_enough_evidence"
    return Verdict(claim=claim, label=label, confidence=0.9, reasoning="stub")


async def _aggregate(verdicts: list[Verdict]) -> Assessment:
    if not verdicts:
        return Assessment(label="not_enough_evidence", score=0.0)
    supported = sum(1 for verdict in verdicts if verdict.label == "supported")
    score = supported / len(verdicts)
    label = "supported" if score >= 0.5 else "refuted"  # noqa: PLR2004 - simple stub threshold.
    return Assessment(label=label, score=score)


def _stub_components(retriever: Retriever = _retrieve) -> Components:
    return Components(
        claim_processor=_process,
        query_generator=_generate,
        retriever=retriever,
        verifier=_verify,
        aggregator=_aggregate,
    )


def _dummy_components() -> Components:
    return Components(
        claim_processor=DummyClaimProcessor(),
        query_generator=DummyQueryGenerator(),
        retriever=DummyRetriever(),
        verifier=DummyVerifier(),
        aggregator=DummyAggregator(),
    )


# ---------------------------------------------------------------------------
# build_graph: the default spine wiring + result assembly
# ---------------------------------------------------------------------------


def test_build_graph_runs_end_to_end() -> None:
    result = build_graph().run(
        Input(content="The sky is blue. Water is wet."), state=PipelineState(), deps=_stub_components()
    )

    assert [v.claim.text for v in result.verdicts] == ["The sky is blue", "Water is wet"]
    assert all(v.label == "supported" for v in result.verdicts)
    assert result.assessment.label == "supported"
    assert result.assessment.score == 1.0
    # Each verdict carries the evidence it was reached on, aligned to its claim.
    assert result.input.content == "The sky is blue. Water is wet."
    assert all(v.evidence.claim == v.claim for v in result.verdicts)


def test_build_graph_preserves_claim_order() -> None:
    delays = {"a": 0.03, "b": 0.0, "c": 0.0}

    async def slow_retrieve(query: Query) -> Evidence:
        await asyncio.sleep(delays.get(query.claim.text, 0.0))
        return Evidence(claim=query.claim, sources=[Source(content=f"e:{query.claim.text}")])

    result = build_graph().run(
        Input(content="a. b. c."), state=PipelineState(), deps=_stub_components(slow_retrieve)
    )

    # Source order survives nondeterministic branch completion.
    assert [v.claim.text for v in result.verdicts] == ["a", "b", "c"]
    assert [v.evidence.claim.text for v in result.verdicts] == ["a", "b", "c"]


def test_build_graph_zero_claims() -> None:
    result = build_graph().run(Input(content="   "), state=PipelineState(), deps=_stub_components())

    assert result.verdicts == []
    assert result.input.content == "   "
    assert result.assessment.label == "not_enough_evidence"


def test_build_graph_duplicate_claims() -> None:
    result = build_graph().run(Input(content="dup. dup."), state=PipelineState(), deps=_stub_components())

    assert [v.claim.text for v in result.verdicts] == ["dup", "dup"]
    assert len(result.verdicts) == 2


def test_build_graph_records_input() -> None:
    state = PipelineState()

    build_graph().run(Input(content="The sky is blue."), state=state, deps=_stub_components())

    assert state.input == Input(content="The sky is blue.")


# ---------------------------------------------------------------------------
# Pipeline: the text-in / result-out surface
# ---------------------------------------------------------------------------


def test_Pipeline_run_coerces_str() -> None:
    pipeline = Pipeline(build_graph(), _stub_components())

    result = pipeline.run("The sky is blue. Water is wet.")

    assert result.input.content == "The sky is blue. Water is wet."
    assert [v.claim.text for v in result.verdicts] == ["The sky is blue", "Water is wet"]


def test_Pipeline_run_accepts_input() -> None:
    pipeline = Pipeline(build_graph(), _stub_components())

    result = pipeline.run(Input(content="Water is wet."))

    assert result.input.content == "Water is wet."
    assert [v.claim.text for v in result.verdicts] == ["Water is wet"]


def test_Pipeline_arun() -> None:
    pipeline = Pipeline(build_graph(), _stub_components())

    result = asyncio.run(pipeline.arun("The sky is blue."))

    assert result.input.content == "The sky is blue."
    assert result.assessment.label == "supported"


def test_Pipeline_run_with_dummy_components() -> None:
    pipeline = Pipeline(build_graph(), _dummy_components())

    result = pipeline.run("The sky is blue.")

    assert result.input.content == "The sky is blue."
    assert [v.claim for v in result.verdicts] == [Claim(text="The sky is blue.")]
    assert len(result.verdicts) == 1
    assert result.verdicts[0].evidence.sources == []
    assert [v.label for v in result.verdicts] == ["not_enough_evidence"]
    assert result.assessment.label == "not_enough_evidence"
    assert result.assessment.score == 0.0
