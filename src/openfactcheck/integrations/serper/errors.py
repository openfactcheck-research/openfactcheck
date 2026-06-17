"""Error hierarchy for the Serper.dev integration."""


class SerperError(Exception):
    """Base error for every Serper.dev integration failure."""


class SerperConfigError(SerperError):
    """The client is missing required configuration, such as the API key."""


class SerperRequestError(SerperError):
    """A request to the Serper.dev API failed or returned an error status."""
