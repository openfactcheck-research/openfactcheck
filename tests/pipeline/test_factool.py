"""Tests for the Factool pipeline wiring.

The pipeline's components are replaced with plain async stubs (patched at the
factory's import site) so the graph wiring is exercised without LLM or network
calls. The components themselves are tested under ``tests/components/factool``.
"""

import asyncio
from collections.abc import Callable

import pytest
from pytest_mock import MockerFixture

from openfactcheck.components.types import Assessment, Claim, Evidence, Input, Query, Report, Source, Verdict
from openfactcheck.graph import GraphEvent, NodeEmitted, RunFinished
from openfactcheck.pipeline import FactoolPipeline, factool


async def _process(text: Input, *, on_partial: Callable[[object], None] | None = None) -> list[Claim]:
    claims = [Claim(text=sentence.strip()) for sentence in text.content.split(".") if sentence.strip()]
    if on_partial is not None:
        on_partial(claims)
    return claims


async def _generate(claim: Claim, *, on_partial: Callable[[object], None] | None = None) -> Query:
    query = Query(claim=claim, questions=[f"is '{claim.text}' true?"])
    if on_partial is not None:
        on_partial(query)
    return query


async def _retrieve(query: Query) -> Evidence:
    return Evidence(claim=query.claim, sources=[Source(content=f"evidence for {query.claim.text}")])


async def _verify(claim: Claim, evidence: Evidence, *, on_partial: Callable[[object], None] | None = None) -> Verdict:
    label = "supported" if evidence.sources else "not_enough_evidence"
    verdict = Verdict(claim=claim, label=label, confidence=0.9, reasoning="stub")
    if on_partial is not None:
        on_partial(verdict)
    return verdict


async def _aggregate(verdicts: list[Verdict]) -> Assessment:
    if not verdicts:
        return Assessment(label="not_enough_evidence", score=0.0)
    supported = sum(1 for verdict in verdicts if verdict.label == "supported")
    return Assessment(label="supported", score=supported / len(verdicts))


def _patch_components(mocker: MockerFixture, *, retriever: Callable[[Query], object] = _retrieve) -> None:
    mocker.patch("openfactcheck.pipeline.factool.FactoolClaimProcessor", return_value=_process)
    mocker.patch("openfactcheck.pipeline.factool.FactoolQueryGenerator", return_value=_generate)
    mocker.patch("openfactcheck.pipeline.factool.FactoolRetriever", return_value=retriever)
    mocker.patch("openfactcheck.pipeline.factool.FactoolVerifier", return_value=_verify)
    mocker.patch("openfactcheck.pipeline.factool.FactoolAggregator", return_value=_aggregate)


@pytest.fixture
def pipeline(mocker: MockerFixture) -> FactoolPipeline:
    """A Factool pipeline with its components replaced by stubs."""
    _patch_components(mocker)
    return factool(chat=mocker.Mock(), serper=mocker.Mock())


# ---------------------------------------------------------------------------
# The graph wiring the factory builds
# ---------------------------------------------------------------------------


def test_factool_runs_end_to_end(pipeline: FactoolPipeline) -> None:
    result = pipeline.run("The sky is blue. Water is wet.")

    assert [v.claim.text for v in result.verdicts] == ["The sky is blue", "Water is wet"]
    assert all(v.label == "supported" for v in result.verdicts)
    assert result.assessment.label == "supported"
    assert result.assessment.score == 1.0
    assert result.input.content == "The sky is blue. Water is wet."
    # Each verdict carries the evidence it was reached on, aligned to its claim.
    assert all(v.evidence is not None and v.evidence.claim == v.claim for v in result.verdicts)


def test_factool_preserves_claim_order(mocker: MockerFixture) -> None:
    delays = {"a": 0.03, "b": 0.0, "c": 0.0}

    async def slow_retrieve(query: Query) -> Evidence:
        await asyncio.sleep(delays.get(query.claim.text, 0.0))
        return Evidence(claim=query.claim, sources=[Source(content=f"e:{query.claim.text}")])

    _patch_components(mocker, retriever=slow_retrieve)
    pipeline = factool(chat=mocker.Mock(), serper=mocker.Mock())

    result = pipeline.run("a. b. c.")

    # Source order survives nondeterministic branch completion.
    assert [v.claim.text for v in result.verdicts] == ["a", "b", "c"]


def test_factool_zero_claims(pipeline: FactoolPipeline) -> None:
    result = pipeline.run("   ")

    assert result.verdicts == []
    assert result.assessment.label == "not_enough_evidence"


def test_factool_records_input(pipeline: FactoolPipeline) -> None:
    result = pipeline.run("The sky is blue.")

    assert result.input == Input(content="The sky is blue.")


# ---------------------------------------------------------------------------
# FactoolPipeline: the text-in / result-out surface
# ---------------------------------------------------------------------------


def test_FactoolPipeline_run_coerces_str(pipeline: FactoolPipeline) -> None:
    result = pipeline.run("Water is wet.")

    assert result.input.content == "Water is wet."
    assert [v.claim.text for v in result.verdicts] == ["Water is wet"]


def test_FactoolPipeline_run_accepts_input(pipeline: FactoolPipeline) -> None:
    result = pipeline.run(Input(content="Water is wet."))

    assert result.input.content == "Water is wet."


def test_FactoolPipeline_arun(pipeline: FactoolPipeline) -> None:
    result = asyncio.run(pipeline.arun("The sky is blue."))

    assert result.assessment.label == "supported"


# ---------------------------------------------------------------------------
# FactoolPipeline.astream: node-level events and opt-in token partials
# ---------------------------------------------------------------------------


def test_FactoolPipeline_astream_emits_node_events(pipeline: FactoolPipeline) -> None:
    async def collect() -> list[GraphEvent]:
        return [event async for event in pipeline.astream("The sky is blue. Water is wet.")]

    events = asyncio.run(collect())

    assert any(type(event).__name__ == "NodeStarted" for event in events)
    assert isinstance(events[-1], RunFinished)
    assert isinstance(events[-1].output, Report)


def test_FactoolPipeline_astream_omits_partials_by_default(pipeline: FactoolPipeline) -> None:
    async def collect() -> list[GraphEvent]:
        return [event async for event in pipeline.astream("The sky is blue.")]

    events = asyncio.run(collect())

    # The components' on_partial is not bridged unless partial streaming is requested.
    assert not any(isinstance(event, NodeEmitted) for event in events)


def test_FactoolPipeline_astream_streams_partials_when_requested(pipeline: FactoolPipeline) -> None:
    async def collect() -> list[GraphEvent]:
        return [event async for event in pipeline.astream("The sky is blue.", stream_partials=True)]

    events = asyncio.run(collect())

    assert any(isinstance(event, NodeEmitted) for event in events)
