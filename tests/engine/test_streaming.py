"""Tests for streaming pipeline execution."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest
from pytest_mock import MockerFixture

from openfactcheck.components.types import Claim, Result, Verdict
from openfactcheck.engine.events import (
    FinishedEvent,
    NodeEmittedEvent,
    NodeFinishedEvent,
    NodeStartedEvent,
    OutputEvent,
)
from openfactcheck.engine.executor import stream_pipeline
from openfactcheck.graph import NodeEmitted, NodeFinished, NodeStarted, RunFinished
from openfactcheck.graph.forks import ForkStackItem

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"blocks": {"blocks": list(blocks)}}


async def test_stream_pipeline_emits_output_then_finished() -> None:
    """A print block streams its line as an output event, then a finished event closes the run."""
    pipeline = _pipeline(
        {"type": "text_print", "inputs": {"TEXT": {"block": {"type": "text", "fields": {"TEXT": "hi"}}}}},
    )

    events = [event async for event in stream_pipeline(pipeline)]

    assert any(isinstance(e, OutputEvent) and e.text == "hi" for e in events)
    assert isinstance(events[-1], FinishedEvent)
    assert events[-1].success
    assert events[-1].output == "hi"


async def test_stream_pipeline_forwards_node_events_from_openfactcheck(mocker: MockerFixture) -> None:
    """The openfactcheck block forwards each graph step as a node event and captures the final result."""
    result = Result(verdicts=[Verdict(claim=Claim(text="c"), label="supported", reasoning="ok")])

    async def fake_astream(_content: str) -> AsyncIterator[object]:
        yield NodeStarted(node_id="claim_processor", fork_stack=())
        yield NodeFinished(node_id="claim_processor", output=[], duration=0.1, fork_stack=())
        yield NodeStarted(node_id="verifier", fork_stack=())
        yield NodeFinished(node_id="verifier", output=None, duration=0.2, fork_stack=())
        yield RunFinished(output=result)

    checker = mocker.patch("openfactcheck.OpenFactCheck")
    checker.return_value.astream = fake_astream

    pipeline = _pipeline(
        {
            "type": "text_input",
            "fields": {"INPUT_TEXT": "some claim"},
            "next": {"block": {"type": "openfactcheck", "fields": {"PIPELINE": "factool"}}},
        },
    )

    events = [event async for event in stream_pipeline(pipeline)]

    started = [e.node_id for e in events if isinstance(e, NodeStartedEvent)]
    finished = [e.node_id for e in events if isinstance(e, NodeFinishedEvent)]
    assert started == ["claim_processor", "verifier"]
    assert finished == ["claim_processor", "verifier"]
    assert isinstance(events[-1], FinishedEvent)
    assert events[-1].success
    assert '"supported"' in events[-1].output


async def test_stream_pipeline_streams_claims_reasoning_and_verdicts(mocker: MockerFixture) -> None:
    """The claim processor's claims, a verifier's partial reasoning, and its verdict stream with branch indices."""
    claims = [Claim(text="c0"), Claim(text="c1")]
    verdict = Verdict(claim=claims[0], label="refuted", reasoning="wrong", correction="fix")
    branch0 = (ForkStackItem(fork_id="map", fork_run_id="r", branch_index=0),)

    async def fake_astream(_content: str) -> AsyncIterator[object]:
        yield NodeFinished(node_id="factool/claim_processor", output=claims, duration=0.1, fork_stack=())
        yield NodeStarted(node_id="factool/verifier", fork_stack=branch0)
        yield NodeEmitted(node_id="factool/verifier", data=SimpleNamespace(reasoning="the evidence"), fork_stack=branch0)
        yield NodeFinished(node_id="factool/verifier", output=verdict, duration=0.2, fork_stack=branch0)
        yield RunFinished(output=Result(verdicts=[verdict]))

    checker = mocker.patch("openfactcheck.OpenFactCheck")
    checker.return_value.astream = fake_astream

    pipeline = _pipeline(
        {
            "type": "text_input",
            "fields": {"INPUT_TEXT": "x"},
            "next": {"block": {"type": "openfactcheck", "fields": {"PIPELINE": "factool"}}},
        },
    )
    events = [event async for event in stream_pipeline(pipeline)]

    claim_step = next(e for e in events if isinstance(e, NodeFinishedEvent) and e.node_id == "factool/claim_processor")
    assert claim_step.output == ["c0", "c1"]

    reasoning = next(e for e in events if isinstance(e, NodeEmittedEvent))
    assert reasoning.branch == 0
    assert reasoning.data == {"reasoning": "the evidence"}

    verdict_step = next(e for e in events if isinstance(e, NodeFinishedEvent) and e.node_id == "factool/verifier")
    assert verdict_step.branch == 0
    assert verdict_step.output == {"label": "refuted", "reasoning": "wrong", "correction": "fix", "error": None}


async def test_stream_pipeline_reports_a_failed_run() -> None:
    """A block that fails yields a finished event marked unsuccessful with the error."""
    pipeline = _pipeline({"type": "openfactcheck", "fields": {"PIPELINE": "factool"}})

    events = [event async for event in stream_pipeline(pipeline)]

    assert isinstance(events[-1], FinishedEvent)
    assert not events[-1].success
    assert "input text" in (events[-1].error or "").lower()
