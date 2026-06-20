"""The runnable fact-check pipeline and the default graph that powers it.

A [`Pipeline`][Pipeline] pairs a built
[`Graph`][Graph] with the [`Components`][Components] that fill
it, exposing a plain ``run(text) -> Report`` surface so a caller never touches the graph's
``state``/``deps`` plumbing. [`build_graph`][build_graph] builds the
default claim-to-verdict topology; an established pipeline pairs that graph with a component family (see the
``factool`` module).

```python
pipeline = Pipeline(build_graph(), components)
result = pipeline.run("The capital of Australia is Sydney.")
```
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from openfactcheck.components.protocols import (
    Aggregator,
    ClaimProcessor,
    QueryGenerator,
    Retriever,
    Reviser,
    Verifier,
)
from openfactcheck.components.types import Claim, Evidence, Input, Query, Report, Verdict
from openfactcheck.graph import Graph, GraphBuilder, GraphEvent, RunOptions, StepContext


@dataclass(frozen=True, slots=True)
class Components:
    """The fact-check components a pipeline run draws on, injected as dependencies."""

    claim_processor: ClaimProcessor
    """Produces atomic claims from the input."""

    query_generator: QueryGenerator
    """Generates search queries for one claim."""

    retriever: Retriever
    """Fetches evidence for one claim's queries."""

    verifier: Verifier
    """Judges one claim against its evidence."""

    aggregator: Aggregator
    """Combines the per-claim verdicts into the overall judgment."""

    reviser: Reviser | None = None
    """Rewrites the input to fix its errors. Required only when the graph is built with revision."""


@dataclass
class PipelineState:
    """Run-scoped state for a fact-check run.

    Carries the original input from the entry step to the assembly step. The
    entry step runs once before any fan-out, so recording the input here is
    free of races.
    """

    input: Input | None = None
    """The run's original input, recorded by the entry step for assembly."""


def build_graph(*, revise: bool = False) -> Graph[Input, Report, PipelineState, Components]:
    """Build the fact-check graph.

    The graph records the input, processes it into claims, fans out to generate
    queries, retrieve evidence, and verify each claim concurrently, collects the
    checked claims, and assembles them with an overall judgment into a result.
    With ``revise`` set, a final step rewrites the input to fix its errors and
    records the result on the report. Supply the components as ``deps`` and a
    fresh [`PipelineState`][PipelineState] as ``state`` when running it, or wrap
    it in a [`Pipeline`][Pipeline] that does so.

    Args:
        revise: Append a revision step that rewrites the input from the verdicts'
            corrections. The graph's [`Components`][Components] must then carry a
            [`reviser`][Components.reviser].

    Returns:
        A built [`Graph`][Graph] taking an [`Input`][Input] and returning a [`Report`][Report].
    """
    g = GraphBuilder(
        deps_type=Components,
        input_type=Input,
        output_type=Report,
        state_type=PipelineState,
    )

    @g.step_node
    async def claim_processor(ctx: StepContext[Input, PipelineState, Components]) -> list[Claim]:
        ctx.state.input = ctx.inputs
        return await ctx.deps.claim_processor(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    @g.step_node
    async def query_generator(ctx: StepContext[Claim, PipelineState, Components]) -> Query:
        return await ctx.deps.query_generator(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    @g.step_node
    async def retriever(ctx: StepContext[Query, PipelineState, Components]) -> Evidence:
        return await ctx.deps.retriever(ctx.inputs)

    @g.step_node
    async def verifier(ctx: StepContext[Evidence, PipelineState, Components]) -> Verdict:
        verdict = await ctx.deps.verifier(ctx.inputs.claim, ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)
        return verdict.model_copy(update={"evidence": ctx.inputs})

    @g.step_node
    async def aggregator(ctx: StepContext[list[Verdict], PipelineState, Components]) -> Report:
        assessment = await ctx.deps.aggregator(ctx.inputs)
        if ctx.state.input is None:
            raise RuntimeError("pipeline input was not recorded before assembly")
        return Report(input=ctx.state.input, verdicts=list(ctx.inputs), assessment=assessment)

    spine = [
        g.edge_from(g.start_node).to(claim_processor),
        g.edge_from(claim_processor).map().to(query_generator),
        g.edge_from(query_generator).to(retriever),
        g.edge_from(retriever).to(verifier),
        g.edge_from(verifier).collect().to(aggregator),
    ]
    if not revise:
        g.add(*spine, g.edge_from(aggregator).to(g.end_node))
        return g.build()

    @g.step_node
    async def reviser(ctx: StepContext[Report, PipelineState, Components]) -> Report:
        if ctx.deps.reviser is None:
            raise RuntimeError("the graph was built with revise=True but no reviser component was supplied")
        report = ctx.inputs
        revision = await ctx.deps.reviser(report.input, report.verdicts, on_partial=ctx.emit if ctx.streaming else None)
        return report.model_copy(update={"revision": revision})

    g.add(
        *spine,
        g.edge_from(aggregator).to(reviser),
        g.edge_from(reviser).to(g.end_node),
    )
    return g.build()


@dataclass(frozen=True, slots=True)
class Pipeline:
    """A ready-to-run fact-check pipeline: text in, a result out.

    Pairs a built graph with the components that fill it, and hides the graph's
    run-time plumbing (wrapping the input, a fresh state, and the component
    dependencies) behind [`run`][Pipeline.run], its async peer [`arun`][Pipeline.arun], and the
    event-streaming [`astream`][Pipeline.astream].
    """

    graph: Graph[Input, Report, PipelineState, Components]
    """The built graph this pipeline runs."""

    components: Components
    """The components injected as the graph's dependencies on each run."""

    def run(self, text: str | Input) -> Report:
        """Fact-check text and return the assembled result.

        Args:
            text: The content to check, as a string or an
                [`Input`][Input].

        Returns:
            The completed fact-check result.
        """
        source = text if isinstance(text, Input) else Input(content=text)
        return self.graph.run(source, state=PipelineState(), deps=self.components)

    async def arun(self, text: str | Input) -> Report:
        """Fact-check text and return the assembled result.

        Args:
            text: The content to check, as a string or an
                [`Input`][Input].

        Returns:
            The completed fact-check result.
        """
        source = text if isinstance(text, Input) else Input(content=text)
        return await self.graph.arun(source, state=PipelineState(), deps=self.components)

    def astream(self, text: str | Input, *, stream_partials: bool = False) -> AsyncIterator[GraphEvent]:
        """Fact-check text and stream progress events as the run unfolds.

        Yields the run's node-level events: a node started, then finished (or
        failed), and a final run-finished. With ``stream_partials`` set, the
        streaming-capable components also surface their in-progress result as
        [`NodeEmitted`][openfactcheck.graph.NodeEmitted] events while they run, for
        token-by-token progress.

        Args:
            text: The content to check, as a string or an
                [`Input`][Input].
            stream_partials: Also stream each component's in-progress result, not
                just the node-level events.

        Returns:
            An async iterator over the run's [`GraphEvent`][GraphEvent]s.
        """
        source = text if isinstance(text, Input) else Input(content=text)
        options = RunOptions(stream_node_data=stream_partials)
        return self.graph.astream(source, state=PipelineState(), deps=self.components, options=options)
