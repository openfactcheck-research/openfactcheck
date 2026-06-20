"""Tests for the FactcheckGPT pipeline wiring.

The pipeline's components are replaced with plain async stubs (patched at the
factory's import site) so the graph wiring, including the closing revision step,
is exercised without LLM or network calls. The components themselves are tested
under ``tests/components/factcheckgpt``.
"""

import asyncio
from collections.abc import Callable

import pytest
from pytest_mock import MockerFixture

from openfactcheck.components.types import Assessment, Claim, Evidence, Input, Query, Report, Source, Verdict
from openfactcheck.graph import GraphEvent, RunFinished
from openfactcheck.pipeline import FactcheckGPTPipeline, factcheckgpt


async def _process(text: Input, *, on_partial: Callable[[object], None] | None = None) -> list[Claim]:
    return [Claim(text=sentence.strip()) for sentence in text.content.split(".") if sentence.strip()]


async def _generate(claim: Claim, *, on_partial: Callable[[object], None] | None = None) -> Query:
    return Query(claim=claim, questions=[f"is '{claim.text}' true?"])


async def _retrieve(query: Query) -> Evidence:
    return Evidence(claim=query.claim, sources=[Source(content=f"evidence for {query.claim.text}")])


async def _verify(claim: Claim, evidence: Evidence, *, on_partial: Callable[[object], None] | None = None) -> Verdict:
    return Verdict(claim=claim, label="refuted", confidence=0.9, reasoning="stub", correction=f"corrected {claim.text}")


async def _aggregate(verdicts: list[Verdict]) -> Assessment:
    return Assessment(label="non_factual" if verdicts else "not_enough_evidence")


async def _revise(text: Input, verdicts: list[Verdict], *, on_partial: Callable[[object], None] | None = None) -> str:
    return f"revised: {text.content} ({len(verdicts)} claims)"


@pytest.fixture
def pipeline(mocker: MockerFixture) -> FactcheckGPTPipeline:
    """A FactcheckGPT pipeline with its components replaced by stubs."""
    mocker.patch("openfactcheck.pipeline.factcheckgpt.FactcheckGPTClaimProcessor", return_value=_process)
    mocker.patch("openfactcheck.pipeline.factcheckgpt.FactcheckGPTQueryGenerator", return_value=_generate)
    mocker.patch("openfactcheck.pipeline.factcheckgpt.FactcheckGPTRetriever", return_value=_retrieve)
    mocker.patch("openfactcheck.pipeline.factcheckgpt.FactcheckGPTVerifier", return_value=_verify)
    mocker.patch("openfactcheck.pipeline.factcheckgpt.FactcheckGPTAggregator", return_value=_aggregate)
    mocker.patch("openfactcheck.pipeline.factcheckgpt.FactcheckGPTReviser", return_value=_revise)
    return factcheckgpt(chat=mocker.Mock(), serper=mocker.Mock())


def test_factcheckgpt_runs_end_to_end(pipeline: FactcheckGPTPipeline) -> None:
    result = pipeline.run("The sky is green. Grass is purple.")

    assert [v.claim.text for v in result.verdicts] == ["The sky is green", "Grass is purple"]
    assert result.assessment.label == "non_factual"
    assert result.input.content == "The sky is green. Grass is purple."


def test_factcheckgpt_sets_revision(pipeline: FactcheckGPTPipeline) -> None:
    result = pipeline.run("The sky is green.")

    assert result.revision == "revised: The sky is green. (1 claims)"


def test_FactcheckGPTPipeline_arun(pipeline: FactcheckGPTPipeline) -> None:
    result = asyncio.run(pipeline.arun("The sky is green."))

    assert result.revision == "revised: The sky is green. (1 claims)"


def test_FactcheckGPTPipeline_astream_runs_revision_node(pipeline: FactcheckGPTPipeline) -> None:
    async def collect() -> list[GraphEvent]:
        return [event async for event in pipeline.astream("The sky is green.")]

    events = asyncio.run(collect())

    assert any(getattr(event, "node_id", None) == "reviser" for event in events)
    assert isinstance(events[-1], RunFinished)
    assert isinstance(events[-1].output, Report)
    assert events[-1].output.revision == "revised: The sky is green. (1 claims)"
