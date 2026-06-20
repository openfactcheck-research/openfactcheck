"""Web evidence retrieval by scraping Google search results.

Build a [`GoogleScraperClient`][GoogleScraperClient] and call
[`retrieve`][GoogleScraperClient.retrieve]; it searches Google, scrapes the
result pages, and returns the passages most relevant to the query as typed
[`Passage`][Passage] models. Import from
``openfactcheck.integrations.google_scraper``.

Needs the ``factcheckgpt`` extra (``pip install openfactcheck[factcheckgpt]``)
for HTML parsing and cross-encoder reranking. No search API key is used, so
retrieval is best-effort and subject to Google rate-limiting.

Example:
    ```python
    from openfactcheck.integrations.google_scraper import GoogleScraperClient

    client = GoogleScraperClient()
    passages = await client.retrieve("who founded openai")
    print(passages[0].url)
    ```
"""

from openfactcheck.integrations.google_scraper.client import (
    DEFAULT_NUM_RESULTS,
    DEFAULT_RANKER_MODEL,
    DEFAULT_SENTENCES_PER_PASSAGE,
    DEFAULT_SLIDING_DISTANCE,
    DEFAULT_TIMEOUT,
    DEFAULT_TOP_K,
    DEFAULT_USER_AGENT,
    GOOGLE_SEARCH_URL,
    GoogleScraperClient,
)
from openfactcheck.integrations.google_scraper.errors import (
    GoogleScraperConfigError,
    GoogleScraperError,
    GoogleScraperRequestError,
)
from openfactcheck.integrations.google_scraper.responses import Passage

# Client
__all__ = [
    "GoogleScraperClient",
]

# Configuration
__all__ += [
    "DEFAULT_NUM_RESULTS",
    "DEFAULT_RANKER_MODEL",
    "DEFAULT_SENTENCES_PER_PASSAGE",
    "DEFAULT_SLIDING_DISTANCE",
    "DEFAULT_TIMEOUT",
    "DEFAULT_TOP_K",
    "DEFAULT_USER_AGENT",
    "GOOGLE_SEARCH_URL",
]

# Responses
__all__ += [
    "Passage",
]

# Errors
__all__ += [
    "GoogleScraperConfigError",
    "GoogleScraperError",
    "GoogleScraperRequestError",
]
