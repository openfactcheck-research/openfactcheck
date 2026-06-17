"""Tests for DummyRetriever."""

import pytest

from openfactcheck.components import Retriever
from openfactcheck.components.dummy import DummyRetriever
from openfactcheck.types import Claim, Query


def test_DummyRetriever_satisfies_protocol() -> None:
    assert isinstance(DummyRetriever(), Retriever)


@pytest.mark.asyncio(loop_scope="function")
async def test_DummyRetriever_returns_no_sources() -> None:
    retriever = DummyRetriever()
    claim = Claim(text="water is wet")
    query = Query(claim=claim, questions=["is water wet?"])

    evidence = await retriever(query)

    assert evidence.claim == claim
    assert evidence.sources == []
