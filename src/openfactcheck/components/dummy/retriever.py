"""Dummy retriever."""

from dataclasses import dataclass

from openfactcheck.types import Evidence, Query


@dataclass(frozen=True, slots=True)
class DummyRetriever:
    """Retriever that fetches no evidence.

    Returns an empty evidence set for any query, which turns the pipeline into
    closed-book verification.
    """

    async def __call__(self, query: Query) -> Evidence:
        """Return empty evidence for ``query``.

        Args:
            query: The claim and its search questions; ignored.

        Returns:
            Evidence attached to the query's claim with no sources.
        """
        return Evidence(claim=query.claim, sources=[])
