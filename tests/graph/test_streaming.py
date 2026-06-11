"""Tests for streaming progress events and the on_event observer hook."""

import asyncio

from openfactcheck.graph import (
    GraphBuilder,
    GraphEvent,
    NodeFinished,
    NodeStarted,
    RunFinished,
    RunOptions,
    StepContext,
)


def _two_step_graph() -> GraphBuilder[None, None, str, str]:
    g = GraphBuilder[None, None, str, str]()

    @g.step
    async def upper(ctx: StepContext[None, None, str]) -> str:
        return ctx.inputs.upper()

    @g.step
    async def exclaim(ctx: StepContext[None, None, str]) -> str:
        return f"{ctx.inputs}!"

    g.add(
        g.edge_from(g.start_node).to(upper),
        g.edge_from(upper).to(exclaim),
        g.edge_from(exclaim).to(g.end_node),
    )
    return g


def test_Graph_astream_emits_node_and_run_events() -> None:
    graph = _two_step_graph().build()

    async def collect() -> list[GraphEvent]:
        return [event async for event in graph.astream("hi", state=None, deps=None)]

    events = asyncio.run(collect())

    started = [e.node_id for e in events if isinstance(e, NodeStarted)]
    finished = [e.node_id for e in events if isinstance(e, NodeFinished)]
    assert started == ["upper", "exclaim"]
    assert finished == ["upper", "exclaim"]
    assert isinstance(events[-1], RunFinished)
    assert events[-1].output == "HI!"


def test_Graph_on_event_observes_each_event() -> None:
    graph = _two_step_graph().build()
    seen: list[str] = []

    def observe(event: GraphEvent) -> None:
        seen.append(type(event).__name__)

    result = graph.run("hi", state=None, deps=None, options=RunOptions(on_event=observe))

    assert result == "HI!"
    assert seen == ["NodeStarted", "NodeFinished", "NodeStarted", "NodeFinished", "RunFinished"]
