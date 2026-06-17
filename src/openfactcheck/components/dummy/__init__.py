"""Deterministic dummy components.

A complete set of placeholder components: each satisfies a category contract but
performs no real work. Wiring them all runs a pipeline end to end with no
external dependencies, which makes them handy as placeholders and as test
fixtures.
"""

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
