"""Tests for FactoolVerifier. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components import Verifier
from openfactcheck.components.factool import FactoolVerifier
from openfactcheck.types import Claim, Evidence, Source


class _FakeClient:
    def __init__(self, result: object) -> None:
        self._result = result

    async def acompletion_as(self, messages: object, response_model: object) -> object:
        return self._result


def test_FactoolVerifier_satisfies_protocol() -> None:
    assert isinstance(FactoolVerifier(client=_FakeClient(None)), Verifier)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactoolVerifier_factual_claim_is_supported() -> None:
    # Factool emits the literal string "None" for the no-error case; it normalises to None.
    client = _FakeClient(SimpleNamespace(reasoning="ok", factuality=True, error="None", correction="None"))
    verifier = FactoolVerifier(client=client)
    claim = Claim(text="the earth is round")

    verdict = await verifier(claim, Evidence(claim=claim, sources=[Source(content="it is round")]))

    assert verdict.label == "supported"
    assert verdict.confidence is None
    assert verdict.error is None
    assert verdict.correction is None


@pytest.mark.asyncio(loop_scope="function")
async def test_FactoolVerifier_non_factual_claim_is_refuted_with_correction() -> None:
    client = _FakeClient(
        SimpleNamespace(reasoning="contradicted", factuality=False, error="not flat", correction="the earth is round")
    )
    verifier = FactoolVerifier(client=client)
    claim = Claim(text="the earth is flat")

    verdict = await verifier(claim, Evidence(claim=claim, sources=[]))

    assert verdict.label == "refuted"
    assert verdict.error == "not flat"
    assert verdict.correction == "the earth is round"
