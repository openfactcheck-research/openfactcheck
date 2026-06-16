"""Public API for the components layer.

A component is a callable implementing one of the category contracts:
``ClaimProcessor``, ``Retriever``, ``Verifier``, and ``Aggregator`` (plus the
optional ``QueryGenerator``). Any implementation of a contract is
interchangeable with any other. Import the contracts from
``openfactcheck.components``; concrete implementations live in subpackages.
"""

from openfactcheck.components.protocols import (
    Aggregator,
    ClaimProcessor,
    QueryGenerator,
    Retriever,
    Verifier,
)

# Component category contracts
__all__ = [
    "Aggregator",
    "ClaimProcessor",
    "QueryGenerator",
    "Retriever",
    "Verifier",
]
