"""Public API for the components layer.

A component is a callable implementing one of the category contracts:
``ClaimProcessor``, ``QueryGenerator``, ``Retriever``, and ``Verifier`` (plus the
optional ``Reviser``). Any implementation of a contract is interchangeable with
any other. The contracts are defined in terms of the data types in this layer
(``Claim``, ``Evidence``, ``Verdict``, and so on). Import both from
``openfactcheck.components``; concrete implementations live in subpackages.
"""

from openfactcheck.components.protocols import (
    ClaimProcessor,
    QueryGenerator,
    Retriever,
    Reviser,
    Verifier,
)
from openfactcheck.components.provenance import Provenance
from openfactcheck.components.types import (
    Claim,
    Evidence,
    Input,
    Query,
    Report,
    ReportSummary,
    Source,
    SourceMetadata,
    Verdict,
    WebMetadata,
)

# Component category contracts
__all__ = [
    "ClaimProcessor",
    "QueryGenerator",
    "Retriever",
    "Reviser",
    "Verifier",
]

# Data types: the fact-checking vocabulary and assembled result
__all__ += [
    "Claim",
    "Evidence",
    "Input",
    "Query",
    "Report",
    "ReportSummary",
    "Source",
    "SourceMetadata",
    "Verdict",
    "WebMetadata",
]

# Shared metadata
__all__ += [
    "Provenance",
]
