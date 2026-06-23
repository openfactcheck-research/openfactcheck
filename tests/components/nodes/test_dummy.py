"""Tests for the dummy node factories.

The dummy components are deterministic placeholders, so a graph wired from their nodes builds and runs with
no mocking, model, or network. The assertions cover construction, node ids, and a full dummy spine running
offline.
"""

from openfactcheck.components import nodes
from openfactcheck.components.types import Input, Verdict
from openfactcheck.graph import GraphBuilder


def _dummy_graph(g: GraphBuilder) -> None:
    claim_processor = nodes.dummy.claim_processor(g)
    query_generator = nodes.dummy.query_generator(g)
    retriever = nodes.dummy.retriever(g)
    verifier = nodes.dummy.verifier(g)
    g.add(
        g.edge_from(g.start_node).to(claim_processor),
        g.edge_from(claim_processor).map().to(query_generator),
        g.edge_from(query_generator).to(retriever),
        g.edge_from(retriever).to(verifier),
        g.edge_from(verifier).collect().to(g.end_node),
    )


def test_dummy_nodes_default_ids() -> None:
    """Each dummy factory registers a node under its namespaced default id."""
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="ids")

    assert nodes.dummy.claim_processor(g).id == "dummy/claim_processor"
    assert nodes.dummy.query_generator(g).id == "dummy/query_generator"
    assert nodes.dummy.retriever(g).id == "dummy/retriever"
    assert nodes.dummy.verifier(g).id == "dummy/verifier"


def test_dummy_node_id_override() -> None:
    """A custom node_id is used as the node's id, so a category can appear more than once."""
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="override")

    node = nodes.dummy.verifier(g, node_id="second_verifier")

    assert node.id == "second_verifier"


def test_dummy_spine_runs_offline() -> None:
    """A full dummy spine builds and runs with no mocking, yielding one inconclusive verdict per claim."""
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="dummy")
    _dummy_graph(g)

    result = g.build().run(Input(content="The sky is blue."), state=None, deps=None)

    assert [verdict.claim.text for verdict in result] == ["The sky is blue."]
    assert all(verdict.label == "not_enough_evidence" for verdict in result)


def test_dummy_spine_blank_input() -> None:
    """The dummy claim processor finds nothing in blank input, so the spine collects no verdicts."""
    g = GraphBuilder(input_type=Input, output_type=list[Verdict], name="blank")
    _dummy_graph(g)

    result = g.build().run(Input(content="   "), state=None, deps=None)

    assert result == []
