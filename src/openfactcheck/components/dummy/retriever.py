"""Dummy retriever."""

from dataclasses import dataclass

from openfactcheck.types import Claim, Evidence


@dataclass(frozen=True, slots=True)
class DummyRetriever:
    """Retriever that fetches no evidence.

    Returns an empty evidence set for any claim, which turns the pipeline into
    closed-book verification.
    """

    async def __call__(self, claim: Claim) -> Evidence:
        """Return empty evidence for ``claim``.

        Args:
            claim: Claim to gather evidence for.

        Returns:
            Evidence attached to ``claim`` with no sources.
        """
        return Evidence(claim=claim, sources=[])
