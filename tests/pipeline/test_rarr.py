"""Tests for the RARR pipeline wiring (the research-and-revise cycle).

The components are replaced with plain async stubs (patched at the factory's
import site) so the graph cycle is exercised without LLM or network calls. The
components themselves are tested under ``tests/components/rarr``.
"""

import asyncio
from collections.abc import Callable

import pytest
from pytest_mock import MockerFixture

from openfactcheck.components.types import Assessment, Claim, Evidence, Input, Query, Report, Source, Verdict
from openfactcheck.graph import GraphEvent, RunFinished
from openfactcheck.pipeline import RARRPipeline, rarr

_RARR = "openfactcheck.pipeline.rarr"


async def _process(text: Input, *, on_partial: Callable[[object], None] | None = None) -> list[Claim]:
    return [Claim(text=text.content)]


async def _generate(claim: Claim, *, on_partial: Callable[[object], None] | None = None) -> Query:
    return Query(claim=claim, questions=["q1", "q2"])


async def _retrieve(query: Query) -> list[tuple[str, Source]]:
    return [("q1", Source(content="E1")), ("q2", Source(content="E2"))]


async def _gate(passage: str, question: str, source: Source, *, on_partial: Callable[[object], None] | None = None) -> Verdict:
    claim = Claim(text=passage)
    label = "refuted" if source.content == "E1" else "supported"
    return Verdict(claim=claim, evidence=Evidence(claim=claim, sources=[source]), label=label, reasoning="r")  # type: ignore[arg-type]


async def _edit(passage: str, question: str, source: Source, *, on_partial: Callable[[object], None] | None = None) -> str:
    return f"{passage} <fixed:{source.content}>"


async def _aggregate(verdicts: list[Verdict]) -> Assessment:
    if not verdicts:
        return Assessment(label="not_enough_evidence")
    unchanged = all(verdict.label == "supported" for verdict in verdicts)
    return Assessment(label="unchanged" if unchanged else "revised")


async def _select(questions: list[str], sources: list[Source]) -> list[Source]:
    return sources


def _patch(
    mocker: MockerFixture,
    *,
    retrieve: Callable[[Query], object] = _retrieve,
    gate: Callable[..., object] = _gate,
) -> RARRPipeline:
    mocker.patch(f"{_RARR}.RARRClaimProcessor", return_value=_process)
    mocker.patch(f"{_RARR}.RARRQueryGenerator", return_value=_generate)
    mocker.patch(f"{_RARR}.RARRRetriever", return_value=retrieve)
    mocker.patch(f"{_RARR}.RARRAgreementGate", return_value=gate)
    mocker.patch(f"{_RARR}.RARREditor", return_value=_edit)
    mocker.patch(f"{_RARR}.RARRAggregator", return_value=_aggregate)
    mocker.patch(f"{_RARR}.RARREvidenceSelector", return_value=_select)
    return rarr(chat=mocker.Mock(), serper=mocker.Mock())


@pytest.fixture
def pipeline(mocker: MockerFixture) -> RARRPipeline:
    return _patch(mocker)


def test_rarr_revises_only_on_disagreement(pipeline: RARRPipeline) -> None:
    result = pipeline.run("The sky is green.")

    # E1 disagreed (edited); E2 agreed (left alone). The revision carries only the E1 fix.
    assert result.revision == "The sky is green. <fixed:E1>"
    assert [verdict.label for verdict in result.verdicts] == ["refuted", "supported"]
    assert result.assessment.label == "revised"


def test_rarr_records_input_and_attribution(pipeline: RARRPipeline) -> None:
    result = pipeline.run("The sky is green.")

    assert result.input.content == "The sky is green."
    assert [source.content for source in (result.attribution or [])] == ["E1", "E2"]


def test_rarr_threads_the_edited_passage(mocker: MockerFixture) -> None:
    seen: list[str] = []

    async def recording_gate(passage: str, question: str, source: Source, *, on_partial: object = None) -> Verdict:
        seen.append(passage)
        return await _gate(passage, question, source)

    pipeline = _patch(mocker, gate=recording_gate)

    pipeline.run("The sky is green.")

    # The second check sees the passage as edited by the first: the loop threads state.
    assert seen == ["The sky is green.", "The sky is green. <fixed:E1>"]


def test_rarr_no_evidence_skips_the_loop(mocker: MockerFixture) -> None:
    async def empty_retrieve(query: Query) -> list[tuple[str, Source]]:
        return []

    pipeline = _patch(mocker, retrieve=empty_retrieve)

    result = pipeline.run("The sky is green.")

    assert result.verdicts == []
    assert result.revision == "The sky is green."
    assert result.assessment.label == "not_enough_evidence"
    assert result.attribution == []


def test_RARRPipeline_run_accepts_input(pipeline: RARRPipeline) -> None:
    result = pipeline.run(Input(content="The sky is green."))

    assert result.input.content == "The sky is green."


def test_RARRPipeline_arun(pipeline: RARRPipeline) -> None:
    result = asyncio.run(pipeline.arun("The sky is green."))

    assert result.revision == "The sky is green. <fixed:E1>"


def test_RARRPipeline_astream_runs_revision_laps(pipeline: RARRPipeline) -> None:
    async def collect() -> list[GraphEvent]:
        return [event async for event in pipeline.astream("The sky is green.")]

    events = asyncio.run(collect())

    revise_events = [event for event in events if getattr(event, "node_id", None) == "revise"]
    assert len(revise_events) >= 2  # noqa: PLR2004 - at least a started + finished across the two laps.
    assert isinstance(events[-1], RunFinished)
    assert isinstance(events[-1].output, Report)
