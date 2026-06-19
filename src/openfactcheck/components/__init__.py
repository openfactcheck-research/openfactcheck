"""Public API for the components layer.

A component is a callable implementing one of the category contracts:
``ClaimProcessor``, ``Retriever``, ``Verifier``, and ``Aggregator`` (plus the
optional ``QueryGenerator``). Any implementation of a contract is
interchangeable with any other. The contracts are defined in terms of the data
types in this layer (``Claim``, ``Evidence``, ``Verdict``, and so on). Import
both from ``openfactcheck.components``; concrete implementations live in
subpackages.
"""

from openfactcheck.components.protocols import (
    Aggregator,
    ClaimProcessor,
    QueryGenerator,
    Retriever,
    Verifier,
)
from openfactcheck.components.provenance import Provenance
from openfactcheck.components.types import (
    Assessment,
    Claim,
    Evidence,
    Input,
    Query,
    Report,
    Source,
    SourceMetadata,
    Verdict,
    WebMetadata,
)

# Component category contracts
__all__ = [
    "Aggregator",
    "ClaimProcessor",
    "QueryGenerator",
    "Retriever",
    "Verifier",
]

# Data types: the fact-checking vocabulary and assembled result
__all__ += [
    "Assessment",
    "Claim",
    "Evidence",
    "Input",
    "Query",
    "Report",
    "Source",
    "SourceMetadata",
    "Verdict",
    "WebMetadata",
]

# Shared metadata
__all__ += [
    "Provenance",
]
