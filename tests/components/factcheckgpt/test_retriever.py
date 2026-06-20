"""Tests for FactcheckGPTRetriever. The Google scraper client is faked."""

import pytest

from openfactcheck.components import Retriever
from openfactcheck.components.factcheckgpt import FactcheckGPTRetriever
from openfactcheck.components.types import Claim, Query, WebMetadata
from openfactcheck.integrations.google_scraper import Passage


class _FakeScraper:
    def __init__(self, passages: list[Passage]) -> None:
        self._passages = passages
        self.calls: list[str] = []

    async def retrieve(self, query: str) -> list[Passage]:
        self.calls.append(query)
        return self._passages


def test_FactcheckGPTRetriever_satisfies_protocol() -> None:
    assert isinstance(FactcheckGPTRetriever(scraper=_FakeScraper([])), Retriever)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTRetriever_maps_passages_to_sources() -> None:
    passages = [Passage(text="p1", url="u1", score=0.9), Passage(text="p2", url="u2", score=0.5)]
    scraper = _FakeScraper(passages)
    retriever = FactcheckGPTRetriever(scraper=scraper)
    claim = Claim(text="c")

    evidence = await retriever(Query(claim=claim, questions=["q1", "q2"]))

    # One source per passage, per question (both questions searched).
    assert [source.content for source in evidence.sources] == ["p1", "p2", "p1", "p2"]
    urls = {source.metadata.url for source in evidence.sources if isinstance(source.metadata, WebMetadata)}
    assert urls == {"u1", "u2"}
    assert scraper.calls == ["q1", "q2"]


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTRetriever_no_questions_skips_search() -> None:
    scraper = _FakeScraper([Passage(text="p", url="u", score=1.0)])
    retriever = FactcheckGPTRetriever(scraper=scraper)
    claim = Claim(text="c")

    evidence = await retriever(Query(claim=claim, questions=[]))

    assert evidence.sources == []
    assert scraper.calls == []
