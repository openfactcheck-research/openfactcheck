"""The FactcheckGPT pipeline.

A self-contained wiring of the [FactcheckGPT][openfactcheck.components.factcheckgpt] components onto a
fact-check graph: record the input, extract claims, fan out per claim to generate queries, retrieve
evidence, and verify each claim concurrently, then collect the verdicts, aggregate them, and rewrite the
input to fix its errors. The result is a [`Report`][openfactcheck.components.types.Report] carrying the
revised text. Build one with [`factcheckgpt`][openfactcheck.pipeline.factcheckgpt.factcheckgpt].

```python
pipeline = factcheckgpt(chat)
report = pipeline.run("The capital of Australia is Sydney.")
print(report.revision)
```
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from openfactcheck.chat import ChatClient
from openfactcheck.components.factcheckgpt import (
    FactcheckGPTAggregator,
    FactcheckGPTClaimProcessor,
    FactcheckGPTQueryGenerator,
    FactcheckGPTRetriever,
    FactcheckGPTReviser,
    FactcheckGPTVerifier,
)
from openfactcheck.components.types import Claim, Evidence, Input, Query, Report, Verdict
from openfactcheck.graph import Graph, GraphBuilder, GraphEvent, RunOptions, StepContext
from openfactcheck.integrations.serper import SerperClient


@dataclass
class _State:
    """Run-scoped state for one FactcheckGPT run.

    Carries the original input from the entry step to the assembly step. The
    entry step runs once before any fan-out, so recording it here is race-free.
    """

    input: Input | None = None
    """The run's original input, recorded by the entry step for assembly."""


@dataclass(frozen=True, slots=True)
class FactcheckGPTPipeline:
    """The FactcheckGPT pipeline: text in, a result out.

    Wraps the built graph and hides its run-time plumbing (wrapping the input and
    a fresh state) behind [`run`][FactcheckGPTPipeline.run], its async peer
    [`arun`][FactcheckGPTPipeline.arun], and the event-streaming
    [`astream`][FactcheckGPTPipeline.astream]. Build one with
    [`factcheckgpt`][openfactcheck.pipeline.factcheckgpt.factcheckgpt].
    """

    graph: Graph[Input, Report, _State]
    """The built FactcheckGPT graph this pipeline runs."""

    def run(self, text: str | Input) -> Report:
        """Fact-check text and return the assembled result, including the revised input.

        Args:
            text: The content to check, as a string or an [`Input`][openfactcheck.components.types.Input].

        Returns:
            The completed fact-check result, with the revised text on
            [`revision`][openfactcheck.components.types.Report.revision].
        """
        source = text if isinstance(text, Input) else Input(content=text)
        return self.graph.run(source, state=_State(), deps=None)

    async def arun(self, text: str | Input) -> Report:
        """Fact-check text and return the assembled result, including the revised input.

        Args:
            text: The content to check, as a string or an [`Input`][openfactcheck.components.types.Input].

        Returns:
            The completed fact-check result, with the revised text on
            [`revision`][openfactcheck.components.types.Report.revision].
        """
        source = text if isinstance(text, Input) else Input(content=text)
        return await self.graph.arun(source, state=_State(), deps=None)

    def astream(self, text: str | Input, *, stream_partials: bool = False) -> AsyncIterator[GraphEvent]:
        """Fact-check text and stream progress events as the run unfolds.

        Yields the run's node-level events: a node started, then finished (or
        failed), and a final run-finished. With ``stream_partials`` set, the
        streaming-capable components also surface their in-progress result as
        [`NodeEmitted`][openfactcheck.graph.NodeEmitted] events while they run, for
        token-by-token progress.

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


def factcheckgpt(chat: ChatClient, serper: SerperClient | None = None) -> FactcheckGPTPipeline:
    """Build the FactcheckGPT fact-check pipeline.

    Wires the FactcheckGPT components onto a fact-check graph that ends with a
    revision step. The claim processor, query generator, verifier, and reviser
    run on ``chat``; the retriever runs on ``serper``.

    Args:
        chat: Chat client backing the LLM components. Its model is the caller's
            choice; the paper's recommended default is recorded on the
            FactcheckGPT components' provenance.
        serper: Web-search client for the retriever. Defaults to a
            [`SerperClient`][openfactcheck.integrations.serper.SerperClient] that
            reads its key from the environment.

    Returns:
        A pipeline that runs the FactcheckGPT method end to end, including the
        final revision of the input.
    """
    serper = serper if serper is not None else SerperClient()
    _processor = FactcheckGPTClaimProcessor(client=chat)
    _generator = FactcheckGPTQueryGenerator(client=chat)
    _retriever = FactcheckGPTRetriever(serper=serper)
    _verifier = FactcheckGPTVerifier(client=chat)
    _aggregator = FactcheckGPTAggregator()
    _reviser = FactcheckGPTReviser(client=chat)

    g = GraphBuilder(input_type=Input, output_type=Report, state_type=_State, name="factcheckgpt")

    @g.step_node
    async def claim_processor(ctx: StepContext[Input, _State]) -> list[Claim]:
        ctx.state.input = ctx.inputs
        return await _processor(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    @g.step_node
    async def query_generator(ctx: StepContext[Claim, _State]) -> Query:
        return await _generator(ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)

    @g.step_node
    async def retriever(ctx: StepContext[Query, _State]) -> Evidence:
        return await _retriever(ctx.inputs)

    @g.step_node
    async def verifier(ctx: StepContext[Evidence, _State]) -> Verdict:
        verdict = await _verifier(ctx.inputs.claim, ctx.inputs, on_partial=ctx.emit if ctx.streaming else None)
        return verdict.model_copy(update={"evidence": ctx.inputs})

    @g.step_node
    async def aggregator(ctx: StepContext[list[Verdict], _State]) -> Report:
        assessment = await _aggregator(ctx.inputs)
        if ctx.state.input is None:
            raise RuntimeError("pipeline input was not recorded before assembly")
        return Report(input=ctx.state.input, verdicts=list(ctx.inputs), assessment=assessment)

    @g.step_node
    async def reviser(ctx: StepContext[Report, _State]) -> Report:
        report = ctx.inputs
        revision = await _reviser(report.input, report.verdicts, on_partial=ctx.emit if ctx.streaming else None)
        return report.model_copy(update={"revision": revision})

    g.add(
        g.edge_from(g.start_node).to(claim_processor),
        g.edge_from(claim_processor).map().to(query_generator),
        g.edge_from(query_generator).to(retriever),
        g.edge_from(retriever).to(verifier),
        g.edge_from(verifier).collect().to(aggregator),
        g.edge_from(aggregator).to(reviser),
        g.edge_from(reviser).to(g.end_node),
    )
    return FactcheckGPTPipeline(g.build())
