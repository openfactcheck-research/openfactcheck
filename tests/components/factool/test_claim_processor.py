"""Tests for FactoolClaimProcessor. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components import ClaimProcessor
from openfactcheck.components.factool import FactoolClaimProcessor
from openfactcheck.types import Claim, Input


class _FakeClient:
    def __init__(self, result: object) -> None:
        self._result = result

    async def acompletion_as(self, messages: object, response_model: object) -> object:
        return self._result


def test_FactoolClaimProcessor_satisfies_protocol() -> None:
    assert isinstance(FactoolClaimProcessor(client=_FakeClient(None)), ClaimProcessor)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactoolClaimProcessor_returns_extracted_claims() -> None:
    processor = FactoolClaimProcessor(client=_FakeClient(SimpleNamespace(claims=["a", "b"])))

    result = await processor(Input(content="some text"))

    assert result == [Claim(text="a"), Claim(text="b")]
