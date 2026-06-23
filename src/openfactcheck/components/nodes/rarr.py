"""RARR nodes: the research-and-revise stages, prebuilt as graph nodes.

RARR works on a whole passage rather than atomic claims, and its retrieve-check-edit loop is a cycle, so its
nodes differ from the linear factories:

- [`claim_processor`][claim_processor] emits a single claim (the whole
  passage), so it is wired without a fan-out.
- [`query_generator`][query_generator] lifts RARR's query generator.
- [`retriever_verifier_loop`][retriever_verifier_loop] is a subgraph: it
  retrieves evidence per question, then loops over each piece, checking the passage against it and editing
  the passage to agree when it disagrees. It plugs into a graph as one node.
"""

from dataclasses import dataclass
from typing import Any

from openfactcheck.chat import ChatClient
from openfactcheck.components.rarr import (
    RARRAgreementGate,
    RARRClaimProcessor,
    RARREditor,
    RARRQueryGenerator,
    RARRRetriever,
)
from openfactcheck.components.rarr.retriever import QuestionedSource
from openfactcheck.components.types import Claim, Input, Query, Verdict
from openfactcheck.graph import AnyGraphBuilder, GraphBuilder, Step, StepContext
from openfactcheck.integrations.serper import SerperClient

DEFAULT_MAX_REVISION_STEPS = 200
"""Safety cap on the revision loop. The loop normally stops once all evidence is processed."""


@dataclass(frozen=True, slots=True)
class ResearchResult:
    """The outcome of the retrieve-and-revise loop: the revised passage and the checks behind it."""

    passage: str
    """The passage after every disagreement found has been edited in."""

    pending: tuple[QuestionedSource, ...]
    """The ``(question, evidence)`` pairs still to check; empty once the loop has finished."""

    gates: tuple[Verdict, ...]
    """The agreement check recorded for each processed pair, in order."""


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


def retriever_verifier_loop(
    g: AnyGraphBuilder,
    chat: ChatClient,
    serper: SerperClient | None = None,
    *,
    node_id: str = "rarr/retriever_verifier_loop",
    max_revision_steps: int = DEFAULT_MAX_REVISION_STEPS,
) -> Step[Query, ResearchResult, Any, Any]:
    """Build RARR's retrieve-and-revise cycle as a subgraph and lift it onto ``g`` as one node.

    The subgraph retrieves one piece of evidence per question, then loops: it checks the current passage
    against the next ``(question, evidence)`` pair with the agreement gate and, on disagreement, edits the
    passage to agree before moving on, so each check sees the passage as edited so far. It returns the revised
    passage and the agreement check for each pair.

    The node's input passage is read from the query's claim, so feed it a query whose claim is the passage to
    revise (as [`claim_processor`][claim_processor] produces).

    Args:
        g: The builder to register the node onto.
        chat: Chat client backing the agreement gate and editor.
        serper: Web-search client for retrieval. Defaults to a client that reads its key from the
            environment.
        node_id: Identifier for the node.
        max_revision_steps: Safety cap on revision-loop laps; the loop normally stops once all evidence is
            processed.

    Returns:
        The registered subgraph node.
    """
    retrieve = RARRRetriever(serper=serper if serper is not None else SerperClient())
    gate = RARRAgreementGate(client=chat)
    editor = RARREditor(client=chat)

    inner: GraphBuilder[Query, ResearchResult, Any, Any] = GraphBuilder(
        input_type=Query, output_type=ResearchResult, name="rarr_retriever_verifier_loop"
    )

    @inner.step_node
    async def retriever_start(ctx: StepContext[Query, Any, Any]) -> ResearchResult:
        pairs = await retrieve(ctx.inputs)
        return ResearchResult(passage=ctx.inputs.claim.text, pending=tuple(pairs), gates=())

    @inner.step_node
    async def reviser(ctx: StepContext[ResearchResult, Any, Any]) -> ResearchResult:
        result = ctx.inputs
        question, source = result.pending[0]
        verdict = await gate(result.passage, question, source, on_partial=ctx.emit if ctx.streaming else None)
        passage = (
            await editor(result.passage, question, source, on_partial=ctx.emit if ctx.streaming else None)
            if verdict.label == "refuted"
            else result.passage
        )
        return ResearchResult(passage=passage, pending=result.pending[1:], gates=(*result.gates, verdict))

    more_pending = inner.decision_node(ResearchResult, node_id="more_pending")
    inner.add(
        inner.edge_from(inner.start_node).to(retriever_start),
        inner.edge_from(retriever_start).to(more_pending),
        more_pending.when(lambda result: len(result.pending) > 0, reviser, max_iterations=max_revision_steps),
        more_pending.otherwise(inner.end_node),
        inner.edge_from(reviser).to(more_pending),
    )
    return g.subgraph_node(inner.build(), node_id=node_id)
