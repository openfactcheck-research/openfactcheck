"""Typed clients for external services that components depend on.

An integration wraps a third-party service (web search, scrapers, and similar)
behind a small typed client. Integrations are not components: they implement no
category contract and hold no fact-checking domain types. A component depends on
an integration and maps its service-shaped results into the domain types.

Each service lives in its own subpackage, for example
[`serper`][openfactcheck.integrations.serper].
"""
