"""RARR nodes: the research-and-revise stages, prebuilt as graph nodes.

RARR works on a whole passage rather than atomic claims, and its check-and-edit loop is a cycle, so its nodes
differ from the linear factories:

- [`claim_processor`][claim_processor] emits a single claim (the whole passage), so it is wired without a
  fan-out.
- [`query_generator`][query_generator] lifts RARR's query generator.
- [`retriever`][retriever] retrieves evidence per question and seeds the research state.
- [`reviser`][reviser] checks the passage against the next piece of evidence and edits it to agree; run it in a
  [`loop`][openfactcheck.graph.loop] until no evidence is left.
- [`aggregator`][aggregator] consolidates the revised passage and its checks into a result.
"""

from typing import Any

from openfactcheck.chat import ChatClient
from openfactcheck.components.rarr import (
    PROVENANCE,
    RARRAggregator,
    RARRAgreementGate,
    RARRClaimProcessor,
    RARREditor,
    RARRQueryGenerator,
    RARRResearch,
    RARRRetriever,
    RARRReviser,
)
from openfactcheck.components.registry import Pipeline
from openfactcheck.components.types import Claim, Input, Query, Result
from openfactcheck.graph import AnyGraphBuilder, Graph, GraphBuilder, Step, StepContext, chain, loop
from openfactcheck.integrations.serper import SerperClient

DEFAULT_MAX_REVISION_STEPS = 200
"""Safety cap on the revision loop. The loop normally stops once all evidence is processed."""


def claim_processor(
    g: AnyGraphBuilder,
    *,
    node_id: str = "rarr/claim_processor",
) -> Step[Input, Claim, Any, Any]:
    """Lift RARR's claim processor onto ``g`` as a node: input text in, one claim out.

    RARR treats the whole passage as a single claim, so this node emits one claim rather than a list, and is
    wired without a ``map`` fan-out.

    Args:
        g: The builder to register the node onto.
        node_id: Identifier for the node.

    Returns:
        The registered claim-processor node.
    """
    component = RARRClaimProcessor()

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Input, Any, Any]) -> Claim:
        claims = await component(ctx.inputs)
        return claims[0]

    return step


def query_generator(
    g: AnyGraphBuilder,
    chat: ChatClient,
    *,
    node_id: str = "rarr/query_generator",
) -> Step[Claim, Query, Any, Any]:
    """Build RARR's query generator and lift it onto ``g`` as a node: one claim in, its search query out.

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the component.
        node_id: Identifier for the node, used to wire edges and label events.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = RARRQueryGenerator(client=chat)

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Claim, Any, Any]) -> Query:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def retriever(
    g: AnyGraphBuilder,
    serper: SerperClient | None = None,
    *,
    node_id: str = "rarr/retriever",
) -> Step[Query, RARRResearch, Any, Any]:
    """Build RARR's retriever and lift it onto ``g`` as a node: a query in, the seeded research state out.

    Retrieves one piece of evidence per question and seeds the research state with the passage (the query's
    claim) and the ``(question, evidence)`` pairs still to check.

    Args:
        g: The builder to register the node onto.
        serper: Web-search client for retrieval. Defaults to a client that reads its key from the
            environment.
        node_id: Identifier for the node.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = RARRRetriever(serper=serper if serper is not None else SerperClient())

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[Query, Any, Any]) -> RARRResearch:
        pairs = await component(ctx.inputs)
        return RARRResearch(passage=ctx.inputs.claim.text, pending=tuple(pairs), gates=())

    return step


def reviser(
    g: AnyGraphBuilder,
    chat: ChatClient,
    *,
    node_id: str = "rarr/reviser",
) -> Step[RARRResearch, RARRResearch, Any, Any]:
    """Build RARR's reviser (the agreement gate and editor) and lift it onto ``g`` as one node.

    Checks the passage against the next pending pair and edits it to agree on a disagreement. Run it in a
    [`loop`][openfactcheck.graph.loop] until the research state has no pending pairs, so each lap sees the
    passage as edited so far.

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the agreement gate and editor.
        node_id: Identifier for the node.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = RARRReviser(gate=RARRAgreementGate(client=chat), editor=RARREditor(client=chat))

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[RARRResearch, Any, Any]) -> RARRResearch:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def aggregator(
    g: AnyGraphBuilder,
    *,
    node_id: str = "rarr/aggregator",
) -> Step[RARRResearch, Result, Any, Any]:
    """Build RARR's aggregator and lift it onto ``g`` as a node: the research state in, a result out.

    Args:
        g: The builder to register the node onto.
        node_id: Identifier for the node.

    Returns:
        The registered node, ready to wire with [`edge_from`][openfactcheck.graph.GraphBuilder.edge_from].
    """
    component = RARRAggregator()

    @g.step_node(node_id=node_id)
    async def step(ctx: StepContext[RARRResearch, Any, Any]) -> Result:
        return await component(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    return step


def build_graph(*, chat: ChatClient, serper: SerperClient | None = None) -> Graph[Input, Result, None, None]:
    """Wire RARR's research-and-revise pipeline into a runnable graph.

    Treats the input as one passage, generates verification questions, retrieves evidence, then loops the
    check-and-revise step until every ``(question, evidence)`` pair is processed, consolidating the revised
    passage and its agreement checks into a result.

    Args:
        chat: Chat client backing the query generator, agreement gate, and editor.
        serper: Web-search client for retrieval. Defaults to a client that reads its key from the
            environment.

    Returns:
        A graph from input text to the consolidated result.
    """
    g: GraphBuilder[Input, Result, None, None] = GraphBuilder(input_type=Input, output_type=Result, name="rarr")
    g.add(
        *chain(
            g,
            g.start_node,
            claim_processor(g),
            query_generator(g, chat),
            retriever(g, serper),
            loop(
                g,
                reviser(g, chat),
                until=lambda research: len(research.pending) == 0,
                max_iterations=DEFAULT_MAX_REVISION_STEPS,
                input_type=RARRResearch,
                node_id="more_pending",
            ),
            aggregator(g),
            g.end_node,
        )
    )
    return g.build()


PIPELINE = Pipeline(build_graph, PROVENANCE.default_model)
"""The RARR pipeline, discovered through the ``openfactcheck.pipelines`` entry point."""
