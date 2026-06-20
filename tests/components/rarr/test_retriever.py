"""Tests for RARRRetriever. The Serper client is faked."""

from collections.abc import Sequence

import pytest

from openfactcheck.components.rarr import RARRRetriever
from openfactcheck.components.types import Claim, Query, WebMetadata
from openfactcheck.integrations.serper import SearchParams, SearchResponse


class _FakeSerper:
    def __init__(self, responses: list[SearchResponse]) -> None:
        self._responses = responses
        self.calls: list[list[SearchParams | str]] = []

    async def search_batch(self, queries: Sequence[SearchParams | str]) -> list[SearchResponse]:
        self.calls.append(list(queries))
        return self._responses


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRRetriever_pairs_each_question_with_its_top_result() -> None:
    responses = [
        SearchResponse.model_validate(
            {"organic": [{"title": "T1", "link": "u1", "snippet": "s1"}, {"title": "T1b", "link": "u1b", "snippet": "s1b"}]}
        ),
        SearchResponse.model_validate({"organic": [{"title": "T2", "link": "u2", "snippet": "s2"}]}),
    ]
    serper = _FakeSerper(responses)
    retriever = RARRRetriever(serper=serper, num_results=5)

    pairs = await retriever(Query(claim=Claim(text="c"), questions=["q1", "q2"]))

    # One pair per question, holding only the top result, paired with its question.
    assert [(question, source.content) for question, source in pairs] == [("q1", "s1"), ("q2", "s2")]
    first_metadata = pairs[0][1].metadata
    assert isinstance(first_metadata, WebMetadata)
    assert first_metadata.url == "u1"
    # Both questions are searched together, carrying the requested result count.
    assert len(serper.calls[0]) == 2
    assert all(isinstance(param, SearchParams) and param.num == 5 for param in serper.calls[0])


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRRetriever_prefers_answer_box() -> None:
    responses = [
        SearchResponse.model_validate(
            {"answerBox": {"answer": "the answer", "link": "u"}, "organic": [{"title": "T", "link": "u2", "snippet": "s"}]}
        )
    ]
    retriever = RARRRetriever(serper=_FakeSerper(responses))

    pairs = await retriever(Query(claim=Claim(text="c"), questions=["q1"]))

    assert [source.content for _question, source in pairs] == ["the answer"]


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRRetriever_drops_questions_without_results() -> None:
    responses = [
        SearchResponse.model_validate({"organic": [{"title": "T1", "link": "u1", "snippet": "s1"}]}),
        SearchResponse.model_validate({"organic": []}),
    ]
    retriever = RARRRetriever(serper=_FakeSerper(responses))

    pairs = await retriever(Query(claim=Claim(text="c"), questions=["q1", "q2"]))

    assert [question for question, _source in pairs] == ["q1"]


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRRetriever_no_questions_skips_search() -> None:
    serper = _FakeSerper([])
    retriever = RARRRetriever(serper=serper)

    pairs = await retriever(Query(claim=Claim(text="c"), questions=[]))

    assert pairs == []
    assert serper.calls == []
