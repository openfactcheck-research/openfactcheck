"""The RARR pipeline.

A self-contained wiring of the [RARR][openfactcheck.components.rarr] components onto a fact-check graph that
researches and revises a passage. The research stage records the input as one claim, generates verification
questions, and retrieves one piece of evidence per question. The revision stage is a **graph cycle**: one
``(question, evidence)`` pair is checked against the passage per lap, the passage is edited in place when it
disagrees, and a decision loops back until every pair is processed. The result is a
[`Report`][openfactcheck.components.types.Report] carrying the revised text and an attribution report. Build
one with [`rarr`][openfactcheck.pipeline.rarr.rarr].

```python
pipeline = rarr(chat)
report = pipeline.run("The Eiffel Tower was completed in 1850.")
print(report.revision)
```
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from openfactcheck.chat import ChatClient
from openfactcheck.components.rarr import (
    RARRAggregator,
    RARRAgreementGate,
    RARRClaimProcessor,
    RARREditor,
    RARREvidenceSelector,
    RARRQueryGenerator,
    RARRRetriever,
)
from openfactcheck.components.rarr.retriever import QuestionedSource
from openfactcheck.components.types import Claim, Input, Query, Report, Verdict
from openfactcheck.graph import Graph, GraphBuilder, GraphEvent, RunOptions, StepContext
from openfactcheck.integrations.serper import SerperClient

DEFAULT_MAX_REVISION_STEPS = 200
"""Safety cap on the revision loop. The loop normally stops once all evidence is processed."""


@dataclass
class _State:
    """Run-scoped state for one RARR run.

    Carries the original input and the generated questions from the research
    steps to the assembly step, which needs them to build the report and select
    the attribution. The steps that set these run once before the revision loop.
    """

    input: Input | None = None
    """The run's original input, recorded by the entry step for assembly."""

    questions: list[str] = field(default_factory=list[str])
    """Every question generated for the passage, used to select the attribution report."""


@dataclass(frozen=True, slots=True)
class _Revision:
    """The value threaded through the revision loop.

    Each lap consumes the first pending ``(question, evidence)`` pair, possibly
    edits the passage, and records the agreement check, so the value carries the
    passage as edited so far, the pairs still to process, and the checks done.
    """

    passage: str
    """The passage as edited so far."""

    pending: tuple[QuestionedSource, ...]
    """The ``(question, evidence)`` pairs still to check."""

    gates: tuple[Verdict, ...]
    """The agreement checks recorded so far, one per processed pair."""


@dataclass(frozen=True, slots=True)
class RARRPipeline:
    """The RARR pipeline: text in, a result out.

    Wraps the built graph and hides its run-time plumbing (wrapping the input and
    a fresh state) behind [`run`][RARRPipeline.run], its async peer
    [`arun`][RARRPipeline.arun], and the event-streaming
    [`astream`][RARRPipeline.astream]. Build one with
    [`rarr`][openfactcheck.pipeline.rarr.rarr].
    """

    graph: Graph[Input, Report, _State]
    """The built RARR graph this pipeline runs."""

    def run(self, text: str | Input) -> Report:
        """Research and revise text, returning the assembled result.

        Args:
            text: The content to check, as a string or an [`Input`][openfactcheck.components.types.Input].

        Returns:
            The result, with the revised text on
            [`revision`][openfactcheck.components.types.Report.revision] and the
            cited sources on [`attribution`][openfactcheck.components.types.Report.attribution].
        """
        source = text if isinstance(text, Input) else Input(content=text)
        return self.graph.run(source, state=_State(), deps=None)

    async def arun(self, text: str | Input) -> Report:
        """Research and revise text, returning the assembled result.

        Args:
            text: The content to check, as a string or an [`Input`][openfactcheck.components.types.Input].

        Returns:
            The result, with the revised text on
            [`revision`][openfactcheck.components.types.Report.revision] and the
            cited sources on [`attribution`][openfactcheck.components.types.Report.attribution].
        """
        source = text if isinstance(text, Input) else Input(content=text)
        return await self.graph.arun(source, state=_State(), deps=None)

    def astream(self, text: str | Input, *, stream_partials: bool = False) -> AsyncIterator[GraphEvent]:
        """Research and revise text, streaming progress events as the run unfolds.

        Yields the run's node-level events, including one per lap of the revision
        loop. With ``stream_partials`` set, the streaming-capable components also
        surface their in-progress result as
        [`NodeEmitted`][openfactcheck.graph.NodeEmitted] events while they run.

        Args:
            text: The content to check, as a string or an [`Input`][openfactcheck.components.types.Input].
            stream_partials: Also stream each component's in-progress result, not
                just the node-level events.

        Returns:
            An async iterator over the run's [`GraphEvent`][openfactcheck.graph.GraphEvent]s.
        """
        source = text if isinstance(text, Input) else Input(content=text)
        options = RunOptions(stream_node_data=stream_partials)
        return self.graph.astream(source, state=_State(), deps=None, options=options)


def rarr(
    chat: ChatClient,
    serper: SerperClient | None = None,
    *,
    max_revision_steps: int = DEFAULT_MAX_REVISION_STEPS,
) -> RARRPipeline:
    """Build the RARR research-and-revise pipeline.

    Wires the RARR components onto a fact-check graph whose revision stage is a
    cycle. The query generator, agreement gate, and editor run on ``chat``; the
    retriever runs on ``serper``; the evidence selector and aggregator are
    deterministic. Question generation benefits from a chat client with a
    non-zero temperature, since RARR samples it several times for coverage.

    Args:
        chat: Chat client backing the LLM components. Its model is the caller's
            choice; the paper's recommended default is recorded on the RARR
            components' provenance.
        serper: Web-search client for the retriever. Defaults to a
            [`SerperClient`][openfactcheck.integrations.serper.SerperClient] that
            reads its key from the environment.
        max_revision_steps: Safety cap on revision-loop laps; the loop normally
            stops once all evidence is processed.

    Returns:
        A pipeline that runs the RARR method end to end, returning the revised
        text and its attribution report.
    """
    serper = serper if serper is not None else SerperClient()
    _claim_processor = RARRClaimProcessor()
    _query_generator = RARRQueryGenerator(client=chat)
    _retriever = RARRRetriever(serper=serper)
    _agreement_gate = RARRAgreementGate(client=chat)
    _editor = RARREditor(client=chat)
    _aggregator = RARRAggregator()
    _selector = RARREvidenceSelector()

    g = GraphBuilder(input_type=Input, output_type=Report, state_type=_State, name="rarr")

    @g.step_node
    async def claim_processor(ctx: StepContext[Input, _State]) -> Claim:
        ctx.state.input = ctx.inputs
        claims = await _claim_processor(ctx.inputs)
        return claims[0]

    @g.step_node
    async def query_generator(ctx: StepContext[Claim, _State]) -> Query:
        query = await _query_generator(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)
        ctx.state.questions = query.questions
        return query

    @g.step_node
    async def retriever(ctx: StepContext[Query, _State]) -> list[QuestionedSource]:
        return await _retriever(ctx.inputs)

    @g.step_node
    async def start_revision(ctx: StepContext[list[QuestionedSource], _State]) -> _Revision:
        if ctx.state.input is None:
            raise RuntimeError("pipeline input was not recorded before revision")
        return _Revision(passage=ctx.state.input.content, pending=tuple(ctx.inputs), gates=())

    @g.step_node
    async def revise(ctx: StepContext[_Revision, _State]) -> _Revision:
        revision = ctx.inputs
        question, source = revision.pending[0]
        gate = await _agreement_gate(revision.passage, question, source, on_partial=ctx.emit if ctx.streaming else None)
        passage = revision.passage
        if gate.label == "refuted":
            passage = await _editor(revision.passage, question, source, on_partial=ctx.emit if ctx.streaming else None)
        return _Revision(passage=passage, pending=revision.pending[1:], gates=(*revision.gates, gate))

    @g.step_node
    async def assemble(ctx: StepContext[_Revision, _State]) -> Report:
        if ctx.state.input is None:
            raise RuntimeError("pipeline input was not recorded before assembly")
        revision = ctx.inputs
        gates = list(revision.gates)
        assessment = await _aggregator(gates)
        sources = [gate.evidence.sources[0] for gate in gates if gate.evidence and gate.evidence.sources]
        attribution = await _selector(ctx.state.questions, sources)
        return Report(
            input=ctx.state.input,
            verdicts=gates,
            assessment=assessment,
            revision=revision.passage,
            attribution=attribution,
        )

    more = g.decision_node(_Revision, node_id="more")
    g.add(
        g.edge_from(g.start_node).to(claim_processor),
        g.edge_from(claim_processor).to(query_generator),
        g.edge_from(query_generator).to(retriever),
        g.edge_from(retriever).to(start_revision),
        g.edge_from(start_revision).to(more),
        more.when(lambda revision: len(revision.pending) > 0, revise, max_iterations=max_revision_steps),
        more.otherwise(assemble),
        g.edge_from(revise).to(more),
        g.edge_from(assemble).to(g.end_node),
    )
    return RARRPipeline(g.build())
