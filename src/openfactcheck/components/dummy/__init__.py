"""Deterministic dummy components.

A complete set of placeholder components: each satisfies a category contract but
performs no real work. Wiring them all runs a pipeline end to end with no
external dependencies, which makes them handy as placeholders and as test
fixtures.
"""

from collections.abc import Mapping
from typing import TYPE_CHECKING

from openfactcheck.components.dummy.claim_processor import DummyClaimProcessor
from openfactcheck.components.dummy.query_generator import DummyQueryGenerator
from openfactcheck.components.dummy.retriever import DummyRetriever
from openfactcheck.components.dummy.verifier import DummyVerifier
from openfactcheck.components.registry import Component

# Dummy components
__all__ = [
    "DummyClaimProcessor",
    "DummyQueryGenerator",
    "DummyRetriever",
    "DummyVerifier",
]


if TYPE_CHECKING:
    from openfactcheck.components.protocols import (
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


COMPONENTS: Mapping[str, Component] = {
    "claim_processor": Component(factory=DummyClaimProcessor, role="claim_processor"),
    "query_generator": Component(factory=DummyQueryGenerator, role="query_generator"),
    "retriever": Component(factory=DummyRetriever, role="retriever"),
    "verifier": Component(factory=DummyVerifier, role="verifier"),
}
"""The dummy components, discovered through the ``openfactcheck.components`` entry point."""
