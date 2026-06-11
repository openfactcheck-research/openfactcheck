"""The default fact-check pipeline, composed on the graph layer.

[`build_pipeline`][build_pipeline] wires the component contracts into a runnable
[`Graph`][openfactcheck.graph.Graph]: it extracts claims from the input, fans
out over them to retrieve evidence and verify each claim in parallel, collects
the per-claim verdicts, and aggregates them into a result. The components are
supplied per run as [`Components`][Components] dependencies, so any
implementation of a contract can be swapped in without touching the wiring.

```python
graph = build_pipeline()
result = graph.run(Input(content="..."), state=None, deps=components)
```
"""

from dataclasses import dataclass

from openfactcheck.contracts import Aggregator, ClaimExtractor, Retriever, Verifier
from openfactcheck.graph import Graph, GraphBuilder, StepContext
from openfactcheck.types import Claim, Evidence, FactCheckResult, Input, Verdict


@dataclass(frozen=True, slots=True)
class Components:
    """The fact-check components a pipeline run draws on, injected as dependencies."""

    extractor: ClaimExtractor
    """Extracts atomic claims from the input."""

    retriever: Retriever
    """Fetches evidence for one claim."""

    verifier: Verifier
    """Judges one claim against its evidence."""

    aggregator: Aggregator
    """Combines the per-claim verdicts into the overall result."""


def build_pipeline() -> Graph[None, Components, Input, FactCheckResult]:
    """Build the default fact-check graph.

    The returned graph extracts claims, fans out to retrieve and verify each
    claim concurrently, collects the verdicts, and aggregates them. Supply the
    components as ``deps`` when running it.

    Returns:
        A built [`Graph`][openfactcheck.graph.Graph] taking an
        [`Input`][openfactcheck.types.Input] and returning a
        [`FactCheckResult`][openfactcheck.types.FactCheckResult].
    """
    g = GraphBuilder[None, Components, Input, FactCheckResult]()

    @g.step
    async def extract(ctx: StepContext[None, Components, Input]) -> list[Claim]:
        return await ctx.deps.extractor(ctx.inputs)

    @g.step
    async def retrieve(ctx: StepContext[None, Components, Claim]) -> Evidence:
        return await ctx.deps.retriever(ctx.inputs)

    @g.step
    async def verify(ctx: StepContext[None, Components, Evidence]) -> Verdict:
        return await ctx.deps.verifier(ctx.inputs.claim, ctx.inputs)

    verdicts = g.collect(Verdict)

    @g.step
    async def aggregate(ctx: StepContext[None, Components, list[Verdict]]) -> FactCheckResult:
        return await ctx.deps.aggregator(ctx.inputs)

    g.add(
        g.edge_from(g.start_node).to(extract),
        g.edge_from(extract).map().to(retrieve),
        g.edge_from(retrieve).to(verify),
        g.edge_from(verify).to(verdicts),
        g.edge_from(verdicts).to(aggregate),
        g.edge_from(aggregate).to(g.end_node),
    )
    return g.build()
