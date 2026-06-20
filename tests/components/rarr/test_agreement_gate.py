"""Tests for RARRAgreementGate. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components.rarr import RARRAgreementGate
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


@pytest.mark.parametrize(
    ("decision", "label"),
    [("agrees", "supported"), ("disagrees", "refuted"), ("irrelevant", "not_enough_evidence")],
)
@pytest.mark.asyncio(loop_scope="function")
async def test_RARRAgreementGate_maps_decision_to_label(decision: str, label: str) -> None:
    gate = RARRAgreementGate(client=_FakeClient(SimpleNamespace(reasoning="because", decision=decision)))

    verdict = await gate("the passage", "a question?", Source(content="the evidence"))

    assert verdict.label == label
    assert verdict.reasoning == "because"
    assert verdict.claim.text == "the passage"
    assert verdict.evidence is not None
    assert verdict.evidence.sources[0].content == "the evidence"


@pytest.mark.asyncio(loop_scope="function")
async def test_RARRAgreementGate_streams_partials_via_on_partial() -> None:
    partials = [
        SimpleNamespace(reasoning="checking", decision=None),
        SimpleNamespace(reasoning="the dates differ", decision="disagrees"),
    ]
    gate = RARRAgreementGate(client=_FakeClient(None, stream=partials))
    seen: list[SimpleNamespace] = []

    verdict = await gate("the passage", "a question?", Source(content="ev"), on_partial=seen.append)

    assert [partial.reasoning for partial in seen] == ["checking", "the dates differ"]
    assert verdict.label == "refuted"
