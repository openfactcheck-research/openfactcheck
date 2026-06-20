"""Tests for FactcheckGPTReviser. The chat client is faked."""

from types import SimpleNamespace

import pytest

from openfactcheck.components import Reviser
from openfactcheck.components.factcheckgpt import FactcheckGPTReviser
from openfactcheck.components.types import Claim, Input, Verdict


class _RecordingClient:
    def __init__(self, result: object, stream: list[object] | None = None) -> None:
        self._result = result
        self._stream = stream or []
        self.messages: list[object] = []

    async def acompletion_as(self, messages: object, response_model: object) -> object:
        self.messages = messages  # type: ignore[assignment]
        return self._result

    async def astream_as(self, messages: object, response_model: object) -> object:
        for partial in self._stream:
            yield partial


def _verdict(text: str, *, label: str, correction: str | None = None) -> Verdict:
    return Verdict(claim=Claim(text=text), label=label, reasoning="", correction=correction)  # type: ignore[arg-type]


def test_FactcheckGPTReviser_satisfies_protocol() -> None:
    assert isinstance(FactcheckGPTReviser(client=_RecordingClient(None)), Reviser)


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTReviser_returns_revised_text() -> None:
    reviser = FactcheckGPTReviser(client=_RecordingClient(SimpleNamespace(revised="the earth is round")))

    revised = await reviser(Input(content="the earth is flat"), [_verdict("the earth is flat", label="refuted")])

    assert revised == "the earth is round"


def test_FactcheckGPTReviser_true_claims_prefers_corrections() -> None:
    verdicts = [
        _verdict("the earth is flat", label="refuted", correction="the earth is round"),
        _verdict("water is wet", label="supported"),
    ]

    claims = FactcheckGPTReviser._true_claims(verdicts)

    assert claims == "- the earth is round\n- water is wet"


@pytest.mark.asyncio(loop_scope="function")
async def test_FactcheckGPTReviser_streams_partials_via_on_partial() -> None:
    partials = [SimpleNamespace(revised="the earth"), SimpleNamespace(revised="the earth is round")]
    reviser = FactcheckGPTReviser(client=_RecordingClient(None, stream=partials))
    seen: list[SimpleNamespace] = []

    revised = await reviser(Input(content="the earth is flat"), [], on_partial=seen.append)

    assert [partial.revised for partial in seen] == ["the earth", "the earth is round"]
    assert revised == "the earth is round"
