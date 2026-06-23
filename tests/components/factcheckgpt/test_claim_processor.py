"""Tests for FactcheckGPTClaimProcessor. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components import ClaimProcessor
from openfactcheck.components.factcheckgpt import FactcheckGPTClaimProcessor
from openfactcheck.components.types import Claim, Input


class _FakeClient:
    def __init__(self, result: object, stream: list[object] | None = None) -> None:
        self._result = result
        self._stream = stream or []

    async def acompletion_as(self, messages: object, response_model: object) -> object:
        return self._result

    async def astream_as(self, messages: object, response_model: object) -> object:
        for partial in self._stream:
            yield partial


def test_FactcheckGPTClaimProcessor_satisfies_protocol() -> None:
    assert isinstance(FactcheckGPTClaimProcessor(client=_FakeClient(None)), ClaimProcessor)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTClaimProcessor_keeps_only_checkworthy_claims() -> None:
    result_obj = SimpleNamespace(
        claims=["Apple was founded in 1976.", "I think Apple is great."],
        checkworthy=["Yes", "No"],
    )
    processor = FactcheckGPTClaimProcessor(client=_FakeClient(result_obj))

    result = await processor(Input(content="some text"))

    assert result == [Claim(text="Apple was founded in 1976.")]


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTClaimProcessor_no_claims_returns_empty() -> None:
    processor = FactcheckGPTClaimProcessor(client=_FakeClient(SimpleNamespace(claims=[], checkworthy=[])))

    result = await processor(Input(content="some text"))

    assert result == []


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTClaimProcessor_streams_partials_via_on_partial() -> None:
    partials = [
        SimpleNamespace(claims=["a"], checkworthy=["Yes"]),
        SimpleNamespace(claims=["a", "b"], checkworthy=["Yes", "No"]),
    ]
    processor = FactcheckGPTClaimProcessor(client=_FakeClient(None, stream=partials))
    seen: list[SimpleNamespace] = []

    result = await processor(Input(content="some text"), on_partial=seen.append)

    assert [partial.claims for partial in seen] == [["a"], ["a", "b"]]
    assert result == [Claim(text="a")]
