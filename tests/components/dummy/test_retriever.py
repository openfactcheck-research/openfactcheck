"""Tests for DummyRetriever."""

import pytest

from openfactcheck.components import Retriever
from openfactcheck.components.dummy import DummyRetriever
from openfactcheck.types import Claim


def test_DummyRetriever_satisfies_protocol() -> None:
    assert isinstance(DummyRetriever(), Retriever)


@pytest.mark.asyncio(loop_scope="function")
async def test_DummyRetriever_returns_no_sources() -> None:
    retriever = DummyRetriever()
    claim = Claim(text="water is wet")

    evidence = await retriever(claim)

    assert evidence.claim == claim
    assert evidence.sources == []
