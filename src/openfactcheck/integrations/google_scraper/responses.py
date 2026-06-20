"""Typed results from the Google scraper integration."""

from pydantic import BaseModel, ConfigDict


class Passage(BaseModel):
    """A passage scraped from a search result page, scored for a query."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    text: str
    """The passage text extracted from the result page."""

    url: str
    """URL of the page the passage was taken from."""

    score: float
    """Relevance of the passage to the query, as scored by the reranker. Higher is more relevant."""
