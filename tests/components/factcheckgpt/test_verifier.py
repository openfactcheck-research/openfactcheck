"""Tests for FactcheckGPTVerifier. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components import Verifier
from openfactcheck.components.factcheckgpt import FactcheckGPTVerifier
from openfactcheck.components.types import Claim, Evidence, Source


class _FakeClient:
    def __init__(self, result: object, stream: list[object] | None = None) -> None:
        self._result = result
        self._stream = stream or []

    async def acompletion_as(self, messages: object, response_model: object) -> object:
        return self._result

    async def astream_as(self, messages: object, response_model: object) -> object:
        for partial in self._stream:
            yield partial


def test_FactcheckGPTVerifier_satisfies_protocol() -> None:
    assert isinstance(FactcheckGPTVerifier(client=_FakeClient(None)), Verifier)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTVerifier_factual_claim_is_supported() -> None:
    client = _FakeClient(SimpleNamespace(reasoning="ok", factuality=True, error="None", correction="None"))
    verifier = FactcheckGPTVerifier(client=client)
    claim = Claim(text="the earth is round")

    verdict = await verifier(claim, Evidence(claim=claim, sources=[Source(content="it is round")]))

    assert verdict.label == "supported"
    assert verdict.confidence is None
    assert verdict.error is None
    assert verdict.correction is None


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTVerifier_non_factual_claim_is_refuted_with_correction() -> None:
    client = _FakeClient(
        SimpleNamespace(reasoning="contradicted", factuality=False, error="not flat", correction="the earth is round")
    )
    verifier = FactcheckGPTVerifier(client=client)
    claim = Claim(text="the earth is flat")

    verdict = await verifier(claim, Evidence(claim=claim, sources=[]))

    assert verdict.label == "refuted"
    assert verdict.error == "not flat"
    assert verdict.correction == "the earth is round"


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTVerifier_streams_partials_via_on_partial() -> None:
    partials = [
        SimpleNamespace(reasoning="Canberra", factuality=None, error=None, correction=None),
        SimpleNamespace(
            reasoning="Canberra is the capital", factuality=False, error="not Sydney", correction="Canberra"
        ),
    ]
    verifier = FactcheckGPTVerifier(client=_FakeClient(None, stream=partials))
    claim = Claim(text="the capital of Australia is Sydney")
    seen: list[SimpleNamespace] = []

    verdict = await verifier(claim, Evidence(claim=claim, sources=[]), on_partial=seen.append)

    assert [partial.reasoning for partial in seen] == ["Canberra", "Canberra is the capital"]
    assert verdict.label == "refuted"
    assert verdict.correction == "Canberra"
