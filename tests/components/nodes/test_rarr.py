"""Tests for the RARR nodes: the single-claim processor and the flat retrieve-and-revise pipeline.

The RARR components are replaced with plain async stubs (patched at the node module's import site) so the
loop runs without LLM or network calls. The components themselves are tested under ``tests/components/rarr``.
"""

import asyncio
from collections.abc import Callable

import pytest
from pytest_mock import MockerFixture

from openfactcheck.components import nodes
from openfactcheck.components.types import Claim, Evidence, Input, Query, Result, Source, Verdict
from openfactcheck.graph import Graph, GraphBuilder, GraphEvent, RunFinished

_RARR = "openfactcheck.components.nodes.rarr"


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


def _build(
    mocker: MockerFixture,
    *,
    retrieve: Callable[[Query], object] = _retrieve,
    gate: Callable[..., object] = _gate,
) -> Graph[Input, Result, None, None]:
    mocker.patch(f"{_RARR}.RARRClaimProcessor", return_value=_process)
    mocker.patch(f"{_RARR}.RARRQueryGenerator", return_value=_generate)
    mocker.patch(f"{_RARR}.RARRRetriever", return_value=retrieve)
    mocker.patch(f"{_RARR}.RARRAgreementGate", return_value=gate)
    mocker.patch(f"{_RARR}.RARREditor", return_value=_edit)

    return nodes.rarr.build_graph(chat=mocker.Mock(), serper=mocker.Mock())


def test_rarr_loop_revises_only_on_disagreement(mocker: MockerFixture) -> None:
    result = _build(mocker).run(Input(content="The sky is green."), state=None, deps=None)

    # E1 disagreed (edited); E2 agreed (left alone).
    assert result.revision == "The sky is green. <fixed:E1>"
    assert [verdict.label for verdict in result.verdicts] == ["refuted", "supported"]


def test_rarr_loop_threads_the_edited_passage(mocker: MockerFixture) -> None:
    seen: list[str] = []

    async def recording_gate(passage: str, question: str, source: Source, *, on_partial: object = None) -> Verdict:
        seen.append(passage)
        return await _gate(passage, question, source)

    _build(mocker, gate=recording_gate).run(Input(content="The sky is green."), state=None, deps=None)

    # The second check sees the passage as edited by the first.
    assert seen == ["The sky is green.", "The sky is green. <fixed:E1>"]


def test_rarr_loop_no_evidence_skips_the_cycle(mocker: MockerFixture) -> None:
    async def empty_retrieve(query: Query) -> list[tuple[str, Source]]:
        return []

    result = _build(mocker, retrieve=empty_retrieve).run(Input(content="The sky is green."), state=None, deps=None)

    assert result.verdicts == []
    assert result.revision == "The sky is green."


def test_rarr_pipeline_astream_finishes_with_result(mocker: MockerFixture) -> None:
    graph = _build(mocker)

    async def collect() -> list[GraphEvent]:
        return [event async for event in graph.astream(Input(content="The sky is green."), state=None, deps=None)]

    events = asyncio.run(collect())

    node_ids = {getattr(event, "node_id", None) for event in events}
    assert "rarr/reviser" in node_ids
    assert isinstance(events[-1], RunFinished)
    assert isinstance(events[-1].output, Result)


@pytest.mark.asyncio(loop_scope="function")
async def test_rarr_claim_processor_emits_single_claim(mocker: MockerFixture) -> None:
    mocker.patch(f"{_RARR}.RARRClaimProcessor", return_value=_process)
    g = GraphBuilder(input_type=Input, output_type=Claim, name="cp")
    claim_processor = nodes.rarr.claim_processor(g)
    g.add(g.edge_from(g.start_node).to(claim_processor), g.edge_from(claim_processor).to(g.end_node))

    claim = await g.build().arun(Input(content="The sky is green."), state=None, deps=None)

    # One claim (the whole passage), not a list, so the node wires without a map fan-out.
    assert claim == Claim(text="The sky is green.")
