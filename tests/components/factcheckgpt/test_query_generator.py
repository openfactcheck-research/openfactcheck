"""Tests for FactcheckGPTQueryGenerator. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components import QueryGenerator
from openfactcheck.components.factcheckgpt import FactcheckGPTQueryGenerator
from openfactcheck.components.types import Claim


class _FakeClient:
    def __init__(self, result: object, stream: list[object] | None = None) -> None:
        self._result = result
        self._stream = stream or []

    async def acompletion_as(self, messages: object, response_model: object) -> object:
        return self._result

    async def astream_as(self, messages: object, response_model: object) -> object:
        for partial in self._stream:
            yield partial


def test_FactcheckGPTQueryGenerator_satisfies_protocol() -> None:
    assert isinstance(FactcheckGPTQueryGenerator(client=_FakeClient(None)), QueryGenerator)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTQueryGenerator_returns_query_with_questions() -> None:
    generator = FactcheckGPTQueryGenerator(client=_FakeClient(SimpleNamespace(queries=["q1", "q2"])))
    claim = Claim(text="the earth is flat")

    query = await generator(claim)

    assert query.claim == claim
    assert query.questions == ["q1", "q2"]


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTQueryGenerator_streams_partials_via_on_partial() -> None:
    partials = [SimpleNamespace(queries=["q1"]), SimpleNamespace(queries=["q1", "q2"])]
    generator = FactcheckGPTQueryGenerator(client=_FakeClient(None, stream=partials))
    seen: list[SimpleNamespace] = []

    query = await generator(Claim(text="c"), on_partial=seen.append)

    assert [partial.queries for partial in seen] == [["q1"], ["q1", "q2"]]
    assert query.questions == ["q1", "q2"]
