"""Tests for RARRAggregator."""

import pytest

from openfactcheck.components import Aggregator
from openfactcheck.components.rarr import RARRAggregator
from openfactcheck.components.types import Claim, Verdict


def _verdict(label: str) -> Verdict:
    return Verdict(claim=Claim(text="c"), label=label, reasoning="r")  # type: ignore[arg-type]


def test_RARRAggregator_satisfies_protocol() -> None:
    assert isinstance(RARRAggregator(), Aggregator)


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRAggregator_no_checks_is_not_enough_evidence() -> None:
    assessment = await RARRAggregator()([])

    assert assessment.label == "not_enough_evidence"


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRAggregator_all_agree_is_unchanged() -> None:
    assessment = await RARRAggregator()([_verdict("supported"), _verdict("supported")])

    assert assessment.label == "unchanged"


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRAggregator_a_disagreement_is_revised() -> None:
    assessment = await RARRAggregator()([_verdict("supported"), _verdict("refuted")])

    assert assessment.label == "revised"
