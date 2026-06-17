"""Tests for FactoolRetriever. The Serper client is faked."""

from collections.abc import Sequence

import pytest

from openfactcheck.components import Retriever
from openfactcheck.components.factool import FactoolRetriever
from openfactcheck.integrations.serper import SearchParams, SearchResponse
from openfactcheck.types import Claim, Query, WebMetadata


class _FakeSerper:
    def __init__(self, responses: list[SearchResponse]) -> None:
        self._responses = responses
        self.calls: list[list[SearchParams | str]] = []

    async def search_batch(self, queries: Sequence[SearchParams | str]) -> list[SearchResponse]:
        self.calls.append(list(queries))
        return self._responses


def test_FactoolRetriever_satisfies_protocol() -> None:
    assert isinstance(FactoolRetriever(serper=_FakeSerper([])), Retriever)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactoolRetriever_collects_snippets_into_sources() -> None:
    responses = [
        SearchResponse.model_validate(
            {"organic": [{"title": "T1", "link": "u1", "snippet": "s1"}], "answerBox": {"answer": "the answer"}}
        ),
        SearchResponse.model_validate({"organic": [{"title": "T2", "link": "u2", "snippet": "s2"}]}),
    ]
    serper = _FakeSerper(responses)
    retriever = FactoolRetriever(serper=serper, num_results=5)
    claim = Claim(text="c")

    evidence = await retriever(Query(claim=claim, questions=["q1", "q2"]))

    contents = [source.content for source in evidence.sources]
    assert {"the answer", "s1", "s2"} <= set(contents)
    organic = [s for s in evidence.sources if isinstance(s.metadata, WebMetadata)]
    assert {s.metadata.url for s in organic if isinstance(s.metadata, WebMetadata)} == {"u1", "u2"}
    # Both queries are searched together, carrying the requested result count.
    assert len(serper.calls[0]) == 2
    assert all(isinstance(param, SearchParams) and param.num == 5 for param in serper.calls[0])


@pytest.mark.asyncio(loop_scope="function")
async def test_FactoolRetriever_no_questions_skips_search() -> None:
    serper = _FakeSerper([])
    retriever = FactoolRetriever(serper=serper)
    claim = Claim(text="c")

    evidence = await retriever(Query(claim=claim, questions=[]))

    assert evidence.sources == []
    assert serper.calls == []
