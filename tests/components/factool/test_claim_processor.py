"""Tests for FactoolClaimProcessor. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components import ClaimProcessor
from openfactcheck.components.factool import FactoolClaimProcessor
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


def test_FactoolClaimProcessor_satisfies_protocol() -> None:
    assert isinstance(FactoolClaimProcessor(client=_FakeClient(None)), ClaimProcessor)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactoolClaimProcessor_returns_extracted_claims() -> None:
    processor = FactoolClaimProcessor(client=_FakeClient(SimpleNamespace(claims=["a", "b"])))

    result = await processor(Input(content="some text"))

    assert result == [Claim(text="a"), Claim(text="b")]


@pytest.mark.asyncio(loop_scope="function")
async def test_FactoolClaimProcessor_streams_partials_via_on_partial() -> None:
    # The claim list fills in as the model writes it.
    partials = [
        SimpleNamespace(claims=["a"]),
        SimpleNamespace(claims=["a", "b"]),
    ]
    processor = FactoolClaimProcessor(client=_FakeClient(None, stream=partials))
    seen: list[SimpleNamespace] = []

    result = await processor(Input(content="some text"), on_partial=seen.append)

    assert [partial.claims for partial in seen] == [["a"], ["a", "b"]]
    assert result == [Claim(text="a"), Claim(text="b")]
