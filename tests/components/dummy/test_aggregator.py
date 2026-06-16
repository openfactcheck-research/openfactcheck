"""Tests for DummyAggregator."""

import pytest

from openfactcheck.components import Aggregator
from openfactcheck.components.dummy import DummyAggregator
from openfactcheck.types import Claim, Verdict


def test_DummyAggregator_satisfies_protocol() -> None:
    assert isinstance(DummyAggregator(), Aggregator)


@pytest.mark.asyncio(loop_scope="function")
async def test_DummyAggregator_returns_inconclusive_judgment() -> None:
    aggregator = DummyAggregator()
    verdict = Verdict(claim=Claim(text="c"), label="supported", confidence=1.0, reasoning="")

    overall = await aggregator([verdict])

    assert overall.label == "not_enough_evidence"
    assert overall.score == 0.0


@pytest.mark.asyncio(loop_scope="function")
async def test_DummyAggregator_handles_empty_verdicts() -> None:
    aggregator = DummyAggregator()

    overall = await aggregator([])

    assert overall.label == "not_enough_evidence"
    assert overall.score == 0.0
