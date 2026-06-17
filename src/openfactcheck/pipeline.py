"""The default fact-check pipeline, composed on the graph layer.

[`build_pipeline`][build_pipeline] wires the component contracts into a runnable
[`Graph`][openfactcheck.graph.Graph]: it processes the input into claims, fans
out over them to generate queries, retrieve evidence, and verify each claim in
parallel, collects the per-claim reports, and assembles them with an overall
judgment into a result. The components are supplied per run as
[`Components`][Components] dependencies, and the original input rides on
[`PipelineState`][PipelineState], so any implementation of a contract can be
swapped in without touching the wiring.

```python
graph = build_pipeline()
result = graph.run(Input(content="..."), state=PipelineState(), deps=components)
```
"""

from dataclasses import dataclass

from openfactcheck.components.protocols import Aggregator, ClaimProcessor, QueryGenerator, Retriever, Verifier
from openfactcheck.graph import Graph, GraphBuilder, StepContext
from openfactcheck.types import Claim, ClaimReport, Evidence, FactCheckResult, Input, Query


@dataclass(frozen=True, slots=True)
class Components:
    """The fact-check components a pipeline run draws on, injected as dependencies."""

    processor: ClaimProcessor
    """Produces atomic claims from the input."""

    generator: QueryGenerator
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


def build_pipeline() -> Graph[Input, FactCheckResult, PipelineState, Components]:
    """Build the default fact-check graph.

    The returned graph records the input, processes it into claims, fans out to
    generate queries, retrieve evidence, and verify each claim concurrently,
    collects the per-claim reports, and assembles them with an overall judgment
    into a result. Supply the components as ``deps`` and a fresh
    [`PipelineState`][PipelineState] as ``state`` when running it.

    Returns:
        A built [`Graph`][openfactcheck.graph.Graph] taking an
        [`Input`][openfactcheck.types.Input] and returning a
        [`FactCheckResult`][openfactcheck.types.FactCheckResult].
    """
    g = GraphBuilder(
        deps_type=Components,
        input_type=Input,
        output_type=FactCheckResult,
        state_type=PipelineState,
    )

    @g.step_node
    async def process(ctx: StepContext[Input, PipelineState, Components]) -> list[Claim]:
        ctx.state.input = ctx.inputs
        return await ctx.deps.processor(ctx.inputs)

    @g.step_node
    async def generate(ctx: StepContext[Claim, PipelineState, Components]) -> Query:
        return await ctx.deps.generator(ctx.inputs)

    @g.step_node
    async def retrieve(ctx: StepContext[Query, PipelineState, Components]) -> Evidence:
        return await ctx.deps.retriever(ctx.inputs)

    @g.step_node
    async def verify(ctx: StepContext[Evidence, PipelineState, Components]) -> ClaimReport:
        verdict = await ctx.deps.verifier(ctx.inputs.claim, ctx.inputs)
        return ClaimReport(claim=ctx.inputs.claim, evidence=ctx.inputs, verdict=verdict)

    reports = g.collect_node(ClaimReport, node_id="reports")

    @g.step_node
    async def assemble(ctx: StepContext[list[ClaimReport], PipelineState, Components]) -> FactCheckResult:
        overall = await ctx.deps.aggregator([report.verdict for report in ctx.inputs])
        recorded = ctx.state.input
        if recorded is None:  # pragma: no cover - the process step records the input first.
            raise RuntimeError("pipeline input was not recorded before assembly")
        return FactCheckResult(
            input=recorded,
            claims=[report.claim for report in ctx.inputs],
            evidence=[report.evidence for report in ctx.inputs],
            verdicts=[report.verdict for report in ctx.inputs],
            overall_label=overall.label,
            overall_score=overall.score,
        )

    g.add(
        g.edge_from(g.start_node).to(process),
        g.edge_from(process).map().to(generate),
        g.edge_from(generate).to(retrieve),
        g.edge_from(retrieve).to(verify),
        g.edge_from(verify).to(reports),
        g.edge_from(reports).to(assemble),
        g.edge_from(assemble).to(g.end_node),
    )
    return g.build()
