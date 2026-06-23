"""Dummy nodes: the deterministic placeholder components, prebuilt as graph nodes.

Each factory builds a dummy component and lifts it onto a graph as a node, doing the small wiring a step
needs: unwrapping the node's input and forwarding the streaming hook. The dummy components reach no real
conclusions, so a graph wired from these nodes runs end to end with no model or network calls, which makes it
a handy skeleton or test fixture.
"""

from typing import Any

from openfactcheck.components.dummy import (
    DummyClaimProcessor,
    DummyQueryGenerator,
    DummyRetriever,
    DummyVerifier,
)
from openfactcheck.components.types import Claim, Evidence, Input, Query, Verdict
from openfactcheck.graph import AnyGraphBuilder, Step, StepContext

__all__ = [
    "claim_processor",
    "query_generator",
    "retriever",
    "verifier",
]


def claim_processor(
    g: AnyGraphBuilder,
    *,
    node_id: str = "dummy/claim_processor",
) -> Step[Input, list[Claim], Any, Any]:
    """Build the dummy claim processor and lift it onto ``g`` as a node: input text in, the whole text as one claim out.

    Args:
        g: The builder to register the node onto.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = DummyClaimProcessor()

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Input, Any, Any]) -> list[Claim]:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def query_generator(
    g: AnyGraphBuilder,
    *,
    node_id: str = "dummy/query_generator",
) -> Step[Claim, Query, Any, Any]:
    """Build the dummy query generator and lift it onto ``g`` as a node: one claim in, a query with no questions out.

    Args:
        g: The builder to register the node onto.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = DummyQueryGenerator()

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Claim, Any, Any]) -> Query:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def retriever(
    g: AnyGraphBuilder,
    *,
    node_id: str = "dummy/retriever",
) -> Step[Query, Evidence, Any, Any]:
    """Build the dummy retriever and lift it onto ``g`` as a node: a query in, empty evidence out.

    Args:
        g: The builder to register the node onto.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = DummyRetriever()

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Query, Any, Any]) -> Evidence:
        return await component(ctx.inputs)

    return step


def verifier(
    g: AnyGraphBuilder,
    *,
    node_id: str = "dummy/verifier",
) -> Step[Evidence, Verdict, Any, Any]:
    """Build the dummy verifier and lift it onto ``g`` as a node: evidence in, an inconclusive verdict out.

    The node's input is the [`Evidence`][Evidence], which carries the claim it bears on, so the verifier is
    called with that claim and evidence.

    Args:
        g: The builder to register the node onto.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = DummyVerifier()

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Evidence, Any, Any]) -> Verdict:
        return await component(ctx.inputs.claim, ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step
