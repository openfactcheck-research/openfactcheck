"""Tests for RARREvidenceSelector. The cross-encoder is faked."""

import pytest
from pytest_mock import MockerFixture

from openfactcheck.components.rarr import RARREvidenceSelector
from openfactcheck.components.types import Source

_SELECTOR = "openfactcheck.components.rarr.evidence_selector"


class _FakeRanker:
    def __init__(self, *_: object, **__: object) -> None: ...

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        # Score by passage length, so selection is deterministic in tests.
        return [float(len(passage)) for _question, passage in pairs]


@pytest.mark.asyncio(loop_scope="function")
async def test_RARREvidenceSelector_returns_all_within_cap() -> None:
    selector = RARREvidenceSelector(max_selected=5)
    sources = [Source(content="a"), Source(content="b")]

    result = await selector(["q1"], sources)

    assert result == sources


@pytest.mark.asyncio(loop_scope="function")
async def test_RARREvidenceSelector_selects_for_question_coverage(mocker: MockerFixture) -> None:
    mocker.patch(f"{_SELECTOR}.load_cross_encoder", return_value=_FakeRanker)
    selector = RARREvidenceSelector(max_selected=1)
    sources = [Source(content="short"), Source(content="a much longer passage of evidence")]

    result = await selector(["q1", "q2"], sources)

    # The longer passage scores higher under the fake ranker, so it covers best.
    assert [source.content for source in result] == ["a much longer passage of evidence"]


@pytest.mark.asyncio(loop_scope="function")
async def test_RARREvidenceSelector_dedupes_by_content(mocker: MockerFixture) -> None:
    mocker.patch(f"{_SELECTOR}.load_cross_encoder", return_value=_FakeRanker)
    selector = RARREvidenceSelector(max_selected=1)
    sources = [Source(content="dup"), Source(content="dup"), Source(content="a longer unique passage")]

    result = await selector(["q1"], sources)

    assert [source.content for source in result] == ["a longer unique passage"]
