"""Dummy query generator."""

from dataclasses import dataclass

from openfactcheck.types import Claim, Query


@dataclass(frozen=True, slots=True)
class DummyQueryGenerator:
    """Query generator that produces no search questions.

    Wraps the claim in a query with an empty question list, so a paired
    retriever has nothing to search for.
    """

    async def __call__(self, claim: Claim) -> Query:
        """Return a query carrying ``claim`` with no questions.

        Args:
            claim: Claim to generate queries for.

        Returns:
            A query holding ``claim`` and an empty question list.
        """
        return Query(claim=claim, questions=[])
