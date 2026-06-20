"""Tests for FactcheckGPTAggregator."""

import pytest

from openfactcheck.components import Aggregator
from openfactcheck.components.factcheckgpt import FactcheckGPTAggregator
from openfactcheck.components.types import Claim, Verdict


def _verdict(label: str) -> Verdict:
    return Verdict(claim=Claim(text="c"), label=label, reasoning="")  # type: ignore[arg-type]


def test_FactcheckGPTAggregator_satisfies_protocol() -> None:
    assert isinstance(FactcheckGPTAggregator(), Aggregator)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTAggregator_all_supported_is_factual() -> None:
    result = await FactcheckGPTAggregator()([_verdict("supported"), _verdict("supported")])

    assert result.label == "factual"
    assert result.score == 1.0


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTAggregator_any_refuted_is_non_factual() -> None:
    result = await FactcheckGPTAggregator()([_verdict("supported"), _verdict("refuted")])

    assert result.label == "non_factual"
    assert result.score == 0.5


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTAggregator_empty_is_not_enough_evidence() -> None:
    result = await FactcheckGPTAggregator()([])

    assert result.label == "not_enough_evidence"
    assert result.score == 0.0
