"""Tests for DummyVerifier."""

import pytest

from openfactcheck.components import Verifier
from openfactcheck.components.dummy import DummyVerifier
from openfactcheck.types import Claim, Evidence


def test_DummyVerifier_satisfies_protocol() -> None:
    assert isinstance(DummyVerifier(), Verifier)


@pytest.mark.asyncio(loop_scope="function")
async def test_DummyVerifier_returns_inconclusive_verdict() -> None:
    verifier = DummyVerifier()
    claim = Claim(text="the earth is round")
    evidence = Evidence(claim=claim, sources=[])

    verdict = await verifier(claim, evidence)

    assert verdict.claim == claim
    assert verdict.label == "not_enough_evidence"
    assert verdict.confidence == 0.0
