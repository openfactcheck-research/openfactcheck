"""RARR retriever, backed by Serper web search."""

from dataclasses import dataclass

from openfactcheck.components.types import Query, Source, SourceMetadata, WebMetadata
from openfactcheck.integrations.serper import SearchParams, SearchResponse, SerperClient

type QuestionedSource = tuple[str, Source]
"""A search question paired with the single piece of evidence retrieved for it."""


@dataclass(frozen=True, slots=True)
class RARRRetriever:
    """Retrieve one piece of evidence per question via Serper web search, following RARR's method.

    Searches every question in one batch and keeps the single top result for
    each: the answer box or knowledge graph when present, otherwise the first
    organic snippet. Each kept result stays paired with the question that found
    it, since RARR checks the passage against that question during revision.
    Questions that turn up nothing are dropped.
    """

    serper: SerperClient
    """The Serper client used for web search."""

    num_results: int = 5
    """Number of organic results to request for each question."""

    async def __call__(self, query: Query) -> list[QuestionedSource]:
        """Retrieve the top evidence for each of the query's questions.

        Args:
            query: The claim and the search questions to run.

        Returns:
            One ``(question, source)`` pair per question that returned evidence,
            in question order; empty when the query carries no questions or
            nothing is found.
        """
        if not query.questions:
            return []
        params = [SearchParams(q=question, num=self.num_results) for question in query.questions]
        responses = await self.serper.search_batch(params)
        pairs: list[QuestionedSource] = []
        for question, response in zip(query.questions, responses, strict=True):
            source = self._top_source(response)
            if source is not None:
                pairs.append((question, source))
        return pairs

    def _top_source(self, response: SearchResponse) -> Source | None:
        """Pick the single best evidence from a search response, or ``None`` when empty."""
        if (box := response.answer_box) is not None and (content := box.answer or box.snippet):
            return self._source(content, box.link, box.title)
        if (graph := response.knowledge_graph) is not None and graph.description:
            return self._source(graph.description, graph.website, graph.title)
        for result in response.organic:
            if result.snippet:
                return self._source(result.snippet, result.link, result.title)
        return None

    def _source(self, content: str, url: str | None, title: str | None) -> Source:
        """Build a source, attaching web metadata when a URL is present."""
        metadata: SourceMetadata = WebMetadata(url=url, title=title) if url else SourceMetadata()
        return Source(content=content, metadata=metadata)
