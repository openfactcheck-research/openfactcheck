"""Tests for DummyQueryGenerator."""

import pytest

from openfactcheck.components import QueryGenerator
from openfactcheck.components.dummy import DummyQueryGenerator
from openfactcheck.types import Claim


def test_DummyQueryGenerator_satisfies_protocol() -> None:
    assert isinstance(DummyQueryGenerator(), QueryGenerator)


@pytest.mark.asyncio(loop_scope="function")
async def test_DummyQueryGenerator_returns_no_questions() -> None:
    generator = DummyQueryGenerator()
    claim = Claim(text="the earth is round")

    query = await generator(claim)

    assert query.claim == claim
    assert query.questions == []
