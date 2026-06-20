"""Error hierarchy for the Google scraper integration."""


class GoogleScraperError(Exception):
    """Base error for every Google scraper integration failure."""


class GoogleScraperConfigError(GoogleScraperError):
    """A required optional dependency is missing or the client is misconfigured."""


class GoogleScraperRequestError(GoogleScraperError):
    """A search request to Google failed or returned an error status."""
