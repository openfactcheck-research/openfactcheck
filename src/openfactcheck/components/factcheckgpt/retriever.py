"""FactcheckGPT retriever, backed by Google scraping."""

import asyncio
from dataclasses import dataclass

from openfactcheck.components.types import Evidence, Query, Source, WebMetadata
from openfactcheck.integrations.google_scraper import GoogleScraperClient, Passage


@dataclass(frozen=True, slots=True)
class FactcheckGPTRetriever:
    """Retrieve evidence for a claim's queries by scraping Google, following FactcheckGPT's method.

    Runs every search question attached to the claim, scrapes and reranks the
    result pages, and collects the top passages into one evidence set.
    """

    scraper: GoogleScraperClient
    """The Google scraper client used for web retrieval."""

    async def __call__(self, query: Query) -> Evidence:
        """Fetch evidence for ``query``.

        Args:
            query: The claim and the search questions to run.

        Returns:
            Evidence for the claim, with one source per retrieved passage; an
            empty source list when the query carries no questions.
        """
        if not query.questions:
            return Evidence(claim=query.claim, sources=[])
        results = await asyncio.gather(*(self.scraper.retrieve(question) for question in query.questions))
        sources = [self._source(passage) for passages in results for passage in passages]
        return Evidence(claim=query.claim, sources=sources)

    @staticmethod
    def _source(passage: Passage) -> Source:
        """Map a scraped passage onto an evidence source."""
        return Source(content=passage.text, metadata=WebMetadata(url=passage.url, title=None))
