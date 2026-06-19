"""The runnable fact-check pipeline and the default graph that powers it.

A [`Pipeline`][openfactcheck.pipeline.Pipeline] pairs a built
[`Graph`][openfactcheck.graph.Graph] with the [`Components`][openfactcheck.pipeline.Components] that fill
it, exposing a plain ``run(text) -> Report`` surface so a caller never touches the graph's
``state``/``deps`` plumbing. [`build_graph`][openfactcheck.pipeline.build_graph] builds the
default claim-to-verdict topology; an established pipeline pairs that graph with a component family (see the
``factool`` module).

```python
pipeline = Pipeline(build_graph(), components)
result = pipeline.run("The capital of Australia is Sydney.")
```
"""

from dataclasses import dataclass

from openfactcheck.components.protocols import Aggregator, ClaimProcessor, QueryGenerator, Retriever, Verifier
from openfactcheck.components.types import Claim, Evidence, Input, Query, Report, Verdict
from openfactcheck.graph import Graph, GraphBuilder, StepContext


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


@dataclass
class PipelineState:
    """Run-scoped state for a fact-check run.

    Carries the original input from the entry step to the assembly step. The
    entry step runs once before any fan-out, so recording the input here is
    free of races.
    """

    input: Input | None = None
    """The run's original input, recorded by the entry step for assembly."""


def build_graph() -> Graph[Input, Report, PipelineState, Components]:
    """Build the default fact-check graph.

    The returned graph records the input, processes it into claims, fans out to
    generate queries, retrieve evidence, and verify each claim concurrently,
    collects the checked claims, and assembles them with an overall judgment
    into a result. Supply the components as ``deps`` and a fresh
    [`PipelineState`][openfactcheck.pipeline.PipelineState] as ``state`` when running it, or wrap it in a
    [`Pipeline`][openfactcheck.pipeline.Pipeline] that does so.

    Returns:
        A built [`Graph`][openfactcheck.graph.Graph] taking an
        [`Input`][openfactcheck.components.types.Input] and returning a
        [`Report`][openfactcheck.components.types.Report].
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
        return await ctx.deps.claim_processor(ctx.inputs)

    @g.step_node
    async def query_generator(ctx: StepContext[Claim, PipelineState, Components]) -> Query:
        return await ctx.deps.query_generator(ctx.inputs)

    @g.step_node
    async def retriever(ctx: StepContext[Query, PipelineState, Components]) -> Evidence:
        return await ctx.deps.retriever(ctx.inputs)

    @g.step_node
    async def verifier(ctx: StepContext[Evidence, PipelineState, Components]) -> Verdict:
        verdict = await ctx.deps.verifier(ctx.inputs.claim, ctx.inputs)
        return verdict.model_copy(update={"evidence": ctx.inputs})

    @g.step_node
    async def aggregator(ctx: StepContext[list[Verdict], PipelineState, Components]) -> Report:
        assessment = await ctx.deps.aggregator(ctx.inputs)
        if ctx.state.input is None:
            raise RuntimeError("pipeline input was not recorded before assembly")
        return Report(input=ctx.state.input, verdicts=list(ctx.inputs), assessment=assessment)

    g.add(
        g.edge_from(g.start_node).to(claim_processor),
        g.edge_from(claim_processor).map().to(query_generator),
        g.edge_from(query_generator).to(retriever),
        g.edge_from(retriever).to(verifier),
        g.edge_from(verifier).collect().to(aggregator),
        g.edge_from(aggregator).to(g.end_node),
    )
    return g.build()


@dataclass(frozen=True, slots=True)
class Pipeline:
    """A ready-to-run fact-check pipeline: text in, a result out.

    Pairs a built graph with the components that fill it, and hides the graph's
    run-time plumbing (wrapping the input, a fresh state, and the component
    dependencies) behind [`run`][openfactcheck.pipeline.Pipeline.run] and its async peer
    [`arun`][openfactcheck.pipeline.Pipeline.arun].
    """

    graph: Graph[Input, Report, PipelineState, Components]
    """The built graph this pipeline runs."""

    components: Components
    """The components injected as the graph's dependencies on each run."""

    def run(self, text: str | Input) -> Report:
        """Fact-check text and return the assembled result.

        Args:
            text: The content to check, as a string or an
                [`Input`][openfactcheck.components.types.Input].

        Returns:
            The completed fact-check result.
        """
        return self.graph.run(self._as_input(text), state=PipelineState(), deps=self.components)

    async def arun(self, text: str | Input) -> Report:
        """Fact-check text and return the assembled result.

        Args:
            text: The content to check, as a string or an
                [`Input`][openfactcheck.components.types.Input].

        Returns:
            The completed fact-check result.
        """
        return await self.graph.arun(self._as_input(text), state=PipelineState(), deps=self.components)

    @staticmethod
    def _as_input(text: str | Input) -> Input:
        return text if isinstance(text, Input) else Input(content=text)
