"""Tests for RARREditor. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components.rarr import RARREditor
from openfactcheck.components.types import Source


class _FakeClient:
    def __init__(self, result: object, stream: list[object] | None = None) -> None:
        self._result = result
        self._stream = stream or []

    async def acompletion_as(self, messages: object, response_model: object) -> object:
        return self._result

    async def astream_as(self, messages: object, response_model: object) -> object:
        for partial in self._stream:
            yield partial


@pytest.mark.asyncio(loop_scope="function")
async def test_RARREditor_applies_a_small_edit() -> None:
    editor = RARREditor(client=_FakeClient(SimpleNamespace(reasoning="wrong year", fix="Completed in 1889.")))

    result = await editor("Completed in 1850.", "When was it completed?", Source(content="1889"))

    assert result == "Completed in 1889."


@pytest.mark.asyncio(loop_scope="function")
async def test_RARREditor_rejects_an_oversized_edit() -> None:
    huge = "an entirely different and much longer rewrite that changes far too much of the passage"
    editor = RARREditor(client=_FakeClient(SimpleNamespace(reasoning="x", fix=huge)))
    original = "Completed in 1850."

    result = await editor(original, "When?", Source(content="ev"))

    # The edit distance exceeds the caps, so the passage is left unchanged.
    assert result == original


@pytest.mark.asyncio(loop_scope="function")
async def test_RARREditor_blank_fix_keeps_original() -> None:
    editor = RARREditor(client=_FakeClient(SimpleNamespace(reasoning="x", fix="   ")))

    result = await editor("Completed in 1850.", "When?", Source(content="ev"))

    assert result == "Completed in 1850."


@pytest.mark.asyncio(loop_scope="function")
async def test_RARREditor_streams_partials_via_on_partial() -> None:
    partials = [SimpleNamespace(reasoning="wrong", fix="Completed"), SimpleNamespace(reasoning="wrong", fix="Done 1889.")]
    editor = RARREditor(client=_FakeClient(None, stream=partials))
    seen: list[SimpleNamespace] = []

    result = await editor("Done 1850.", "When?", Source(content="1889"), on_partial=seen.append)

    assert [partial.fix for partial in seen] == ["Completed", "Done 1889."]
    assert result == "Done 1889."
