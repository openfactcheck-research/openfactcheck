"""Factool retriever, backed by Serper web search."""

from dataclasses import dataclass

from openfactcheck.components.types import Evidence, Query, Source, SourceMetadata, WebMetadata
from openfactcheck.integrations.serper import SearchParams, SearchResponse, SerperClient


@dataclass(frozen=True, slots=True)
class FactoolRetriever:
    """Retrieve evidence for a claim's queries via Serper web search.

    Searches every query attached to the claim and collects the answer box,
    knowledge graph, and organic snippets into one evidence set.
    """

    serper: SerperClient
    """The Serper client used for web search."""

    num_results: int = 10
    """Number of organic results to request for each query."""

    async def __call__(self, query: Query) -> Evidence:
        """Fetch evidence for ``query``.

        Args:
            query: The claim and the search questions to run.

        Returns:
            Evidence for the claim, with one source per retrieved snippet; an
            empty source list when the query carries no questions.
        """
        if not query.questions:
            return Evidence(claim=query.claim, sources=[])
        params = [SearchParams(q=question, num=self.num_results) for question in query.questions]
        responses = await self.serper.search_batch(params)
        sources = [source for response in responses for source in self._sources(response)]
        return Evidence(claim=query.claim, sources=sources)

    def _sources(self, response: SearchResponse) -> list[Source]:
        """Collect the snippets from one search response into evidence sources."""
        sources: list[Source] = []
        if (box := response.answer_box) is not None and (content := box.answer or box.snippet):
            sources.append(self._source(content, box.link, box.title))
        if (graph := response.knowledge_graph) is not None and graph.description:
            sources.append(self._source(graph.description, graph.website, graph.title))
        sources.extend(
            self._source(result.snippet, result.link, result.title) for result in response.organic if result.snippet
        )
        return sources

    def _source(self, content: str, url: str | None, title: str | None) -> Source:
        """Build a source, attaching web metadata when a URL is present."""
        metadata: SourceMetadata = WebMetadata(url=url, title=title) if url else SourceMetadata()
        return Source(content=content, metadata=metadata)
