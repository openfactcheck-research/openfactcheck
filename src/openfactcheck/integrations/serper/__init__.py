"""Typed async client for the Serper.dev Google Search API.

Build a [`SerperClient`][SerperClient], then call
[`search`][SerperClient.search] or [`scrape`][SerperClient.scrape]; results
come back as typed models. Import from ``openfactcheck.integrations.serper``.

Example:
    ```python
    from openfactcheck.integrations.serper import SerperClient

    client = SerperClient()
    result = await client.search("who founded openai")
    print(result.organic[0].link)
    ```
"""

from openfactcheck.integrations.serper.client import (
    DEFAULT_SCRAPE_BASE_URL,
    DEFAULT_SEARCH_BASE_URL,
    DEFAULT_TIMEOUT,
    SerperClient,
)
from openfactcheck.integrations.serper.config import SerperSpec
from openfactcheck.integrations.serper.errors import SerperConfigError, SerperError, SerperRequestError
from openfactcheck.integrations.serper.params import SearchParams, SerperTimeRange
from openfactcheck.integrations.serper.responses import (
    AnswerBox,
    KnowledgeGraph,
    OrganicResult,
    PeopleAlsoAsk,
    RelatedSearch,
    ScrapeResponse,
    SearchParameters,
    SearchResponse,
    Sitelink,
)

# Client
__all__ = [
    "SerperClient",
]

# Configuration
__all__ += [
    "DEFAULT_SCRAPE_BASE_URL",
    "DEFAULT_SEARCH_BASE_URL",
    "DEFAULT_TIMEOUT",
    "SearchParams",
    "SerperSpec",
    "SerperTimeRange",
]

# Responses
__all__ += [
    "AnswerBox",
    "KnowledgeGraph",
    "OrganicResult",
    "PeopleAlsoAsk",
    "RelatedSearch",
    "ScrapeResponse",
    "SearchParameters",
    "SearchResponse",
    "Sitelink",
]

# Errors
__all__ += [
    "SerperConfigError",
    "SerperError",
    "SerperRequestError",
]
