"""Factool nodes: the Factool knowledge-QA components, prebuilt as graph nodes.

Each factory builds a Factool component and lifts it onto a graph as a node, doing the small wiring a step
needs: unwrapping the node's input and forwarding the streaming hook. Wire the returned nodes with the graph
API, and mix them with other papers' nodes freely.
"""

from typing import Any

from openfactcheck.chat import ChatClient
from openfactcheck.components.factool import (
    PROVENANCE,
    FactoolAggregator,
    FactoolClaimProcessor,
    FactoolQueryGenerator,
    FactoolRetriever,
    FactoolVerifier,
)
from openfactcheck.components.registry import Pipeline
from openfactcheck.components.types import Claim, Evidence, Input, Query, Result, Verdict
from openfactcheck.graph import AnyGraphBuilder, Graph, GraphBuilder, Step, StepContext, chain, per_item
from openfactcheck.integrations.serper import SerperClient

__all__ = [
    "PROVENANCE",
    "aggregator",
    "build_graph",
    "claim_processor",
    "query_generator",
    "retriever",
    "verifier",
]


def claim_processor(
    g: AnyGraphBuilder,
    chat: ChatClient,
    *,
    node_id: str = "factool/claim_processor",
) -> Step[Input, list[Claim], Any, Any]:
    """Build Factool's claim processor and lift it onto ``g`` as a node: input text in, atomic claims out.

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the component.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactoolClaimProcessor(client=chat)

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Input, Any, Any]) -> list[Claim]:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def query_generator(
    g: AnyGraphBuilder,
    chat: ChatClient,
    *,
    node_id: str = "factool/query_generator",
) -> Step[Claim, Query, Any, Any]:
    """Build Factool's query generator and lift it onto ``g`` as a node: one claim in, its search query out.

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the component.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactoolQueryGenerator(client=chat)

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Claim, Any, Any]) -> Query:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def retriever(
    g: AnyGraphBuilder,
    serper: SerperClient | None = None,
    *,
    node_id: str = "factool/retriever",
) -> Step[Query, Evidence, Any, Any]:
    """Build Factool's retriever and lift it onto ``g`` as a node: a query in, evidence out.

    Args:
        g: The builder to register the node onto.
        serper: Web-search client for the retriever. Defaults to a client that reads its key from the
            environment.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactoolRetriever(serper=serper if serper is not None else SerperClient())

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Query, Any, Any]) -> Evidence:
        return await component(ctx.inputs)

    return step


def verifier(
    g: AnyGraphBuilder,
    chat: ChatClient,
    *,
    node_id: str = "factool/verifier",
) -> Step[Evidence, Verdict, Any, Any]:
    """Build Factool's verifier and lift it onto ``g`` as a node: evidence in, a verdict out.

    The node's input is the [`Evidence`][Evidence], which carries the claim it
    bears on, so the verifier is called with that claim and evidence.

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the component.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactoolVerifier(client=chat)

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Evidence, Any, Any]) -> Verdict:
        return await component(ctx.inputs.claim, ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def aggregator(
    g: AnyGraphBuilder,
    *,
    node_id: str = "factool/aggregator",
) -> Step[list[Verdict], Result, Any, Any]:
    """Build Factool's aggregator and lift it onto ``g`` as a node: collected verdicts in, a result out.

    Args:
        g: The builder to register the node onto.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactoolAggregator()

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[list[Verdict], Any, Any]) -> Result:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def build_graph(*, chat: ChatClient, serper: SerperClient | None = None) -> Graph[Input, Result, None, None]:
    """Wire Factool's knowledge-QA pipeline into a runnable graph.

    Extracts claims, then for each claim in parallel generates a query, retrieves evidence, and verifies,
    consolidating the per-claim verdicts into a result at the end.

    Args:
        chat: Chat client backing the claim processor, query generator, and verifier.
        serper: Web-search client for the retriever. Defaults to a client that reads its key from the
            environment.

    Returns:
        A graph from input text to the consolidated result.
    """
    g: GraphBuilder[Input, Result, None, None] = GraphBuilder(input_type=Input, output_type=Result, name="factool")
    g.add(
        *chain(
            g,
            g.start_node,
            claim_processor(g, chat),
            per_item(
                g,
                query_generator(g, chat),
                retriever(g, serper),
                verifier(g, chat),
            ),
            aggregator(g),
            g.end_node,
        )
    )
    return g.build()


PIPELINE = Pipeline(build_graph, PROVENANCE.default_model)
"""The Factool pipeline, discovered through the ``openfactcheck.pipelines`` entry point."""
