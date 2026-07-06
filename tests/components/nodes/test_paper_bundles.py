"""Tests for the paper-bundled node factories (factool, factcheckgpt).

Each bundle builds a paper's component and lifts it onto the graph, so the components are patched at the
bundle's import site (the same pattern as the pipeline tests). The assertions cover construction, node ids,
the claim/evidence split a verifier node does, streaming, and that a paper-shaped graph runs offline. The
factool and factcheckgpt node bodies are the same shape, so the behaviour is exercised on factool and
factcheckgpt gets a smoke test.
"""

import asyncio
from collections.abc import Callable

from pytest_mock import MockerFixture

from openfactcheck.components import factcheckgpt as factcheckgpt_components
from openfactcheck.components import factool as factool_components
from openfactcheck.components import nodes
from openfactcheck.components.types import Claim, Evidence, Input, Query, Result, Source, Verdict
from openfactcheck.graph import GraphBuilder, NodeEmitted, RunOptions

_FACTOOL = "openfactcheck.components.nodes.factool"
_FACTCHECKGPT = "openfactcheck.components.nodes.factcheckgpt"


async def _process(text: Input, *, on_partial: Callable[[object], None] | None = None) -> list[Claim]:
    claims = [Claim(text=sentence.strip()) for sentence in text.content.split(".") if sentence.strip()]
    if on_partial is not None:
        on_partial(claims)
    return claims


async def _generate(claim: Claim, *, on_partial: Callable[[object], None] | None = None) -> Query:
    return Query(claim=claim, questions=[f"is '{claim.text}' true?"])


async def _retrieve(query: Query) -> Evidence:
    return Evidence(claim=query.claim, sources=[Source(content=f"evidence for {query.claim.text}")])


async def _verify(claim: Claim, evidence: Evidence, *, on_partial: Callable[[object], None] | None = None) -> Verdict:
    return Verdict(claim=claim, label="supported", reasoning="stub")


def _patch_factool(mocker: MockerFixture, *, verify: Callable[..., object] = _verify) -> None:
    mocker.patch(f"{_FACTOOL}.FactoolClaimProcessor", return_value=_process)
    mocker.patch(f"{_FACTOOL}.FactoolQueryGenerator", return_value=_generate)
    mocker.patch(f"{_FACTOOL}.FactoolRetriever", return_value=_retrieve)
    mocker.patch(f"{_FACTOOL}.FactoolVerifier", return_value=verify)


def _factool_graph(g: GraphBuilder, mocker: MockerFixture) -> None:
    chat, serper = mocker.Mock(), mocker.Mock()
    claim_processor = nodes.factool.claim_processor(g, chat)
    query_generator = nodes.factool.query_generator(g, chat)
    retriever = nodes.factool.retriever(g, serper)
    verifier = nodes.factool.verifier(g, chat)
    g.add(
        g.edge_from(g.start_node).to(claim_processor),
        g.edge_from(claim_processor).map().to(query_generator),
        g.edge_from(query_generator).to(retriever),
        g.edge_from(retriever).to(verifier),
        g.edge_from(verifier).collect().to(g.end_node),
    )


# ---------------------------------------------------------------------------
# Construction and node ids
# ---------------------------------------------------------------------------


def test_factool_bundle_builds_component_with_chat(mocker: MockerFixture) -> None:
    """The claim-processor bundle constructs the paper component with the given chat client."""
    processor_cls = mocker.patch(f"{_FACTOOL}.FactoolClaimProcessor", return_value=_process)
    chat = mocker.Mock()
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="t")

    node = nodes.factool.claim_processor(g, chat)

    processor_cls.assert_called_once_with(client=chat)
    assert node.id == "factool/claim_processor"


def test_factool_retriever_defaults_serper(mocker: MockerFixture) -> None:
    """The retriever bundle builds a default SerperClient when none is given."""
    serper_cls = mocker.patch(f"{_FACTOOL}.SerperClient")
    retriever_cls = mocker.patch(f"{_FACTOOL}.FactoolRetriever", return_value=_retrieve)
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="t")

    nodes.factool.retriever(g)

    serper_cls.assert_called_once_with()
    retriever_cls.assert_called_once_with(serper=serper_cls.return_value)


def test_factool_node_id_override(mocker: MockerFixture) -> None:
    """A custom node_id is used as the node's id, so a category can appear more than once."""
    mocker.patch(f"{_FACTOOL}.FactoolVerifier", return_value=_verify)
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="ids")

    node = nodes.factool.verifier(g, mocker.Mock(), node_id="second_verifier")

    assert node.id == "second_verifier"


# ---------------------------------------------------------------------------
# Node behaviour (exercised on factool; factcheckgpt shares the shape)
# ---------------------------------------------------------------------------


def test_factool_bundle_runs_end_to_end(mocker: MockerFixture) -> None:
    """A factool-shaped graph wired from the bundle runs offline with stubs."""
    _patch_factool(mocker)
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="factool")
    _factool_graph(g, mocker)

    result = g.build().run(Input(content="The sky is blue. Water is wet."), state=None, deps=None)

    assert [verdict.claim.text for verdict in result] == ["The sky is blue", "Water is wet"]
    assert all(verdict.label == "supported" for verdict in result)


def test_factool_verifier_passes_claim_and_evidence(mocker: MockerFixture) -> None:
    """The verifier node calls the component with the evidence and the claim riding on it."""
    seen: dict[str, object] = {}

    async def recording_verify(claim: Claim, evidence: Evidence, *, on_partial: object = None) -> Verdict:
        seen["claim"] = claim
        seen["evidence"] = evidence
        return Verdict(claim=claim, label="supported", reasoning="stub")

    _patch_factool(mocker, verify=recording_verify)
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="split")
    _factool_graph(g, mocker)

    g.build().run(Input(content="The earth is flat."), state=None, deps=None)

    assert isinstance(seen["evidence"], Evidence)
    assert seen["evidence"].claim == seen["claim"]


def test_factool_zero_claims(mocker: MockerFixture) -> None:
    """A claim processor that finds nothing collects to an empty verdict list."""
    _patch_factool(mocker)
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="empty")
    _factool_graph(g, mocker)

    result = g.build().run(Input(content="   "), state=None, deps=None)

    assert result == []


def test_factool_node_streams_partials_only_when_requested(mocker: MockerFixture) -> None:
    """A streaming-capable node emits NodeEmitted only when the run asks for partials."""
    mocker.patch(f"{_FACTOOL}.FactoolClaimProcessor", return_value=_process)
    g = GraphBuilder(input_type=Input, output_type=list[Claim], name="stream")
    claim_processor = nodes.factool.claim_processor(g, mocker.Mock())
    g.add(g.edge_from(g.start_node).to(claim_processor), g.edge_from(claim_processor).to(g.end_node))
    graph = g.build()

    async def collect(stream: bool) -> list[object]:
        options = RunOptions(stream_node_data=stream)
        return [event async for event in graph.astream(Input(content="The sky is blue."), state=None, deps=None, options=options)]

    streamed = asyncio.run(collect(stream=True))
    quiet = asyncio.run(collect(stream=False))

    assert any(isinstance(event, NodeEmitted) for event in streamed)
    assert not any(isinstance(event, NodeEmitted) for event in quiet)


# ---------------------------------------------------------------------------
# FactcheckGPT bundle
# ---------------------------------------------------------------------------


def test_factcheckgpt_bundle_runs_end_to_end(mocker: MockerFixture) -> None:
    """A factcheckgpt-shaped graph wired from the bundle runs offline with stubs."""
    mocker.patch(f"{_FACTCHECKGPT}.FactcheckGPTClaimProcessor", return_value=_process)
    mocker.patch(f"{_FACTCHECKGPT}.FactcheckGPTQueryGenerator", return_value=_generate)
    mocker.patch(f"{_FACTCHECKGPT}.FactcheckGPTRetriever", return_value=_retrieve)
    mocker.patch(f"{_FACTCHECKGPT}.FactcheckGPTVerifier", return_value=_verify)
    chat, serper = mocker.Mock(), mocker.Mock()

    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="factcheckgpt")
    claim_processor = nodes.factcheckgpt.claim_processor(g, chat)
    query_generator = nodes.factcheckgpt.query_generator(g, chat)
    retriever = nodes.factcheckgpt.retriever(g, serper)
    verifier = nodes.factcheckgpt.verifier(g, chat)
    g.add(
        g.edge_from(g.start_node).to(claim_processor),
        g.edge_from(claim_processor).map().to(query_generator),
        g.edge_from(query_generator).to(retriever),
        g.edge_from(retriever).to(verifier),
        g.edge_from(verifier).collect().to(g.end_node),
    )

    result = g.build().run(Input(content="The sky is blue. Water is wet."), state=None, deps=None)

    assert [verdict.claim.text for verdict in result] == ["The sky is blue", "Water is wet"]
    assert all(verdict.label == "supported" for verdict in result)


def test_bundle_provenance_is_component_provenance() -> None:
    """Each bundle re-exports its paper's provenance, not a copy."""
    assert nodes.factool.PROVENANCE is factool_components.PROVENANCE
    assert nodes.factcheckgpt.PROVENANCE is factcheckgpt_components.PROVENANCE


def test_factcheckgpt_offers_no_reviser_node() -> None:
    """The reviser is deferred to the facade; the bundle exposes no reviser node."""
    assert not hasattr(nodes.factcheckgpt, "reviser")


def test_bundles_offer_an_aggregator_node() -> None:
    """Each standard bundle exposes an aggregator node that consolidates its verdicts into a result."""
    g = GraphBuilder(input_type=list[Verdict], output_type=Result, name="agg")
    aggregator = nodes.factool.aggregator(g)
    g.add(g.edge_from(g.start_node).to(aggregator), g.edge_from(aggregator).to(g.end_node))

    verdicts = [Verdict(claim=Claim(text="The sky is blue"), label="supported", reasoning="stub")]
    result = g.build().run(verdicts, state=None, deps=None)

    assert isinstance(result, Result)
    assert result.verdicts == verdicts
    assert aggregator.id == "factool/aggregator"
    assert hasattr(nodes.factcheckgpt, "aggregator")
