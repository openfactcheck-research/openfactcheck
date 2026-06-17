"""Deterministic dummy components.

A complete set of placeholder components: each satisfies a category contract but
performs no real work. Wiring them all runs a pipeline end to end with no
external dependencies, which makes them handy as placeholders and as test
fixtures.
"""

from typing import TYPE_CHECKING

from openfactcheck.components.dummy.aggregator import DummyAggregator
from openfactcheck.components.dummy.claim_processor import DummyClaimProcessor
from openfactcheck.components.dummy.query_generator import DummyQueryGenerator
from openfactcheck.components.dummy.retriever import DummyRetriever
from openfactcheck.components.dummy.verifier import DummyVerifier

# Dummy components
__all__ = [
    "DummyAggregator",
    "DummyClaimProcessor",
    "DummyQueryGenerator",
    "DummyRetriever",
    "DummyVerifier",
]


if TYPE_CHECKING:
    from openfactcheck.components.protocols import (
        Aggregator,
        ClaimProcessor,
        QueryGenerator,
        Retriever,
        Verifier,
    )

    # Type-only conformance: each dummy component must satisfy its category protocol,
    # so pyright fails the gate the moment one drifts. Absent at runtime.
    _processor: type[ClaimProcessor] = DummyClaimProcessor
    _generator: type[QueryGenerator] = DummyQueryGenerator
    _retriever: type[Retriever] = DummyRetriever
    _verifier: type[Verifier] = DummyVerifier
    _aggregator: type[Aggregator] = DummyAggregator
