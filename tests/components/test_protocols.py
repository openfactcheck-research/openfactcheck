"""Tests for component category Protocols — structural typing compliance."""

import pytest

from openfactcheck.components import Aggregator, ClaimProcessor, QueryGenerator, Retriever, Verifier
from openfactcheck.types import (
    Claim,
    Evidence,
    Input,
    OverallVerdict,
    Query,
    Source,
    Verdict,
)


@pytest.mark.asyncio(loop_scope="function")
async def test_ClaimProcessor_accepts_conforming_implementation() -> None:
    """A class with matching async __call__ satisfies the Protocol and can be invoked."""

    class DummyProcessor:
        async def __call__(self, text: Input) -> list[Claim]:
            return [Claim(text=f"claim from {text.content}")]

    processor: ClaimProcessor = DummyProcessor()

    assert isinstance(processor, ClaimProcessor)
    result = await processor(Input(content="sample"))
    assert result == [Claim(text="claim from sample")]


@pytest.mark.asyncio(loop_scope="function")
async def test_QueryGenerator_accepts_conforming_implementation() -> None:
    """A class with matching async __call__ satisfies the QueryGenerator Protocol."""

    class DummyGenerator:
        async def __call__(self, claim: Claim) -> Query:
            return Query(claim=claim, questions=[f"is {claim.text} true?"])

    generator: QueryGenerator = DummyGenerator()

    assert isinstance(generator, QueryGenerator)
    result = await generator(Claim(text="the sky is blue"))
    assert result.claim.text == "the sky is blue"
    assert result.questions == ["is the sky is blue true?"]


@pytest.mark.asyncio(loop_scope="function")
async def test_Retriever_accepts_conforming_implementation() -> None:
    """A class with matching async __call__ satisfies the Retriever Protocol."""

    class DummyRetriever:
        async def __call__(self, query: Query) -> Evidence:
            return Evidence(claim=query.claim, sources=[Source(content="dummy source")])

    retriever: Retriever = DummyRetriever()

    assert isinstance(retriever, Retriever)
    claim = Claim(text="water is wet")
    result = await retriever(Query(claim=claim, questions=["is water wet?"]))
    assert result.claim.text == "water is wet"
    assert len(result.sources) == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_Verifier_accepts_conforming_implementation() -> None:
    """A class with matching async __call__ satisfies the Verifier Protocol."""

    class DummyVerifier:
        async def __call__(self, claim: Claim, evidence: Evidence) -> Verdict:
            return Verdict(claim=claim, label="supported", confidence=0.9, reasoning="because")

    verifier: Verifier = DummyVerifier()

    assert isinstance(verifier, Verifier)
    claim = Claim(text="the earth is round")
    evidence = Evidence(claim=claim, sources=[])
    result = await verifier(claim, evidence)
    assert result.label == "supported"
    assert result.confidence == 0.9


@pytest.mark.asyncio(loop_scope="function")
async def test_Aggregator_accepts_conforming_implementation() -> None:
    """A class with matching async __call__ satisfies the Aggregator Protocol."""

    class DummyAggregator:
        async def __call__(self, verdicts: list[Verdict]) -> OverallVerdict:
            label = "supported" if verdicts else "not_enough_evidence"
            return OverallVerdict(label=label, score=1.0)

    aggregator: Aggregator = DummyAggregator()

    assert isinstance(aggregator, Aggregator)
    claim = Claim(text="c")
    verdict = Verdict(claim=claim, label="supported", confidence=1.0, reasoning="")
    result = await aggregator([verdict])
    assert result.label == "supported"
    assert result.score == 1.0


@pytest.mark.parametrize(
    "protocol",
    [ClaimProcessor, QueryGenerator, Retriever, Verifier, Aggregator],
    ids=["ClaimProcessor", "QueryGenerator", "Retriever", "Verifier", "Aggregator"],
)
def test_contracts_reject_class_without_call(protocol: type) -> None:
    """A class without __call__ does not satisfy any component Protocol."""

    class Empty:
        pass

    assert not isinstance(Empty(), protocol)
