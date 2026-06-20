"""Tests for RARRQueryGenerator. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components import QueryGenerator
from openfactcheck.components.rarr import RARRQueryGenerator
from openfactcheck.components.types import Claim


class _FakeClient:
    """Returns one queued result per ``acompletion_as`` call; replays ``stream`` for ``astream_as``."""

    def __init__(self, rounds: list[object] | None = None, stream: list[object] | None = None) -> None:
        self._rounds = rounds or []
        self._call = 0
        self._stream = stream or []

    async def acompletion_as(self, messages: object, response_model: object) -> object:
        result = self._rounds[self._call]
        self._call += 1
        return result

    async def astream_as(self, messages: object, response_model: object) -> object:
        for partial in self._stream:
            yield partial


def test_RARRQueryGenerator_satisfies_protocol() -> None:
    assert isinstance(RARRQueryGenerator(client=_FakeClient()), QueryGenerator)


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRQueryGenerator_unions_questions_across_rounds() -> None:
    rounds = [SimpleNamespace(questions=["a", "b"]), SimpleNamespace(questions=["b", "c"])]
    generator = RARRQueryGenerator(client=_FakeClient(rounds=rounds), num_rounds=2)

    query = await generator(Claim(text="passage"))

    # Deduplicated across rounds, first-seen order preserved.
    assert query.questions == ["a", "b", "c"]


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRQueryGenerator_drops_blank_questions() -> None:
    generator = RARRQueryGenerator(client=_FakeClient(rounds=[SimpleNamespace(questions=["a", "  ", ""])]), num_rounds=1)

    query = await generator(Claim(text="passage"))

    assert query.questions == ["a"]


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRQueryGenerator_streams_partials_via_on_partial() -> None:
    partials = [SimpleNamespace(questions=["a"]), SimpleNamespace(questions=["a", "b"])]
    generator = RARRQueryGenerator(client=_FakeClient(stream=partials), num_rounds=1)
    seen: list[SimpleNamespace] = []

    query = await generator(Claim(text="passage"), on_partial=seen.append)

    assert [partial.questions for partial in seen] == [["a"], ["a", "b"]]
    assert query.questions == ["a", "b"]
