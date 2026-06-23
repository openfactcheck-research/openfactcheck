"""FactcheckGPT nodes: the FactcheckGPT components, prebuilt as graph nodes.

Each factory builds a FactcheckGPT component and lifts it onto a graph as a node, doing the small wiring a
step needs: unwrapping the node's input and forwarding the streaming hook. The reviser is not offered as a
node: it needs the original input alongside the verdicts, which the facade supplies, not the graph dataflow.
"""

from typing import Any

from openfactcheck.chat import ChatClient
from openfactcheck.components.factcheckgpt import (
    PROVENANCE,
    FactcheckGPTClaimProcessor,
    FactcheckGPTQueryGenerator,
    FactcheckGPTRetriever,
    FactcheckGPTVerifier,
)
from openfactcheck.components.types import Claim, Evidence, Input, Query, Verdict
from openfactcheck.graph import AnyGraphBuilder, Step, StepContext
from openfactcheck.integrations.serper import SerperClient

__all__ = [
    "PROVENANCE",
    "claim_processor",
    "query_generator",
    "retriever",
    "verifier",
]


def claim_processor(
    g: AnyGraphBuilder,
    chat: ChatClient,
    *,
    node_id: str = "factcheckgpt/claim_processor",
) -> Step[Input, list[Claim], Any, Any]:
    """Build FactcheckGPT's claim processor and lift it onto ``g`` as a node: input text in, atomic claims out.

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the component.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactcheckGPTClaimProcessor(client=chat)

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Input, Any, Any]) -> list[Claim]:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def query_generator(
    g: AnyGraphBuilder,
    chat: ChatClient,
    *,
    node_id: str = "factcheckgpt/query_generator",
) -> Step[Claim, Query, Any, Any]:
    """Build FactcheckGPT's query generator and lift it onto ``g`` as a node: one claim in, its search query out.

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the component.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactcheckGPTQueryGenerator(client=chat)

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Claim, Any, Any]) -> Query:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def retriever(
    g: AnyGraphBuilder,
    serper: SerperClient | None = None,
    *,
    node_id: str = "factcheckgpt/retriever",
) -> Step[Query, Evidence, Any, Any]:
    """Build FactcheckGPT's retriever and lift it onto ``g`` as a node: a query in, evidence out.

    Args:
        g: The builder to register the node onto.
        serper: Web-search client for the retriever. Defaults to a client that reads its key from the
            environment.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactcheckGPTRetriever(serper=serper if serper is not None else SerperClient())

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Query, Any, Any]) -> Evidence:
        return await component(ctx.inputs)

    return step


def verifier(
    g: AnyGraphBuilder,
    chat: ChatClient,
    *,
    node_id: str = "factcheckgpt/verifier",
) -> Step[Evidence, Verdict, Any, Any]:
    """Build FactcheckGPT's verifier and lift it onto ``g`` as a node: evidence in, a verdict out.

    The node's input is the [`Evidence`][Evidence], which carries the claim it
    bears on, so the verifier is called with that claim and evidence.

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the component.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = FactcheckGPTVerifier(client=chat)

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Evidence, Any, Any]) -> Verdict:
        return await component(ctx.inputs.claim, ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step
