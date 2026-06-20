"""Tests for streaming progress events and the on_event observer hook."""

import asyncio

from openfactcheck.graph import (
    GraphBuilder,
    GraphEvent,
    NodeEmitted,
    NodeFinished,
    NodeStarted,
    RunFinished,
    RunOptions,
    StepContext,
)


def _two_step_graph() -> GraphBuilder[str, str]:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def upper(ctx: StepContext[str]) -> str:
        return ctx.inputs.upper()

    @g.step_node
    async def exclaim(ctx: StepContext[str]) -> str:
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


def _emitting_graph() -> GraphBuilder[str, str]:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def echo(ctx: StepContext[str]) -> str:
        ctx.emit(f"tok:{ctx.inputs}")
        ctx.emit("done")
        return ctx.inputs.upper()

    g.add(
        g.edge_from(g.start_node).to(echo),
        g.edge_from(echo).to(g.end_node),
    )
    return g


def test_Graph_astream_discards_node_data_by_default() -> None:
    graph = _emitting_graph().build()

    async def collect() -> list[GraphEvent]:
        return [event async for event in graph.astream("hi", state=None, deps=None)]

    events = asyncio.run(collect())

    assert not any(isinstance(e, NodeEmitted) for e in events)
    assert [type(e).__name__ for e in events] == ["NodeStarted", "NodeFinished", "RunFinished"]


def test_Graph_astream_emits_node_data_when_enabled() -> None:
    graph = _emitting_graph().build()

    async def collect() -> list[GraphEvent]:
        options = RunOptions(stream_node_data=True)
        return [event async for event in graph.astream("hi", state=None, deps=None, options=options)]

    events = asyncio.run(collect())

    emitted = [e for e in events if isinstance(e, NodeEmitted)]
    assert [(e.node_id, e.data) for e in emitted] == [("echo", "tok:hi"), ("echo", "done")]
    # Emissions fall between the node's start and its finish.
    kinds = [type(e).__name__ for e in events]
    assert kinds == ["NodeStarted", "NodeEmitted", "NodeEmitted", "NodeFinished", "RunFinished"]


def test_Graph_astream_node_data_carries_arbitrary_objects() -> None:
    sentinel = object()
    g = GraphBuilder[str, str]()

    @g.step_node
    async def pass_object(ctx: StepContext[str]) -> str:
        ctx.emit(sentinel)
        return ctx.inputs

    g.add(g.edge_from(g.start_node).to(pass_object), g.edge_from(pass_object).to(g.end_node))

    async def collect() -> list[GraphEvent]:
        options = RunOptions(stream_node_data=True)
        return [event async for event in g.build().astream("x", state=None, deps=None, options=options)]

    events = asyncio.run(collect())

    emitted = [e for e in events if isinstance(e, NodeEmitted)]
    assert len(emitted) == 1
    assert emitted[0].data is sentinel


def test_Graph_on_event_includes_node_data_when_enabled() -> None:
    graph = _emitting_graph().build()
    emitted: list[object] = []

    def observe(event: GraphEvent) -> None:
        if isinstance(event, NodeEmitted):
            emitted.append(event.data)

    graph.run("hi", state=None, deps=None, options=RunOptions(on_event=observe, stream_node_data=True))

    assert emitted == ["tok:hi", "done"]


def test_Graph_astream_node_data_tagged_by_fork_branch() -> None:
    g = GraphBuilder[str, list[str]]()

    @g.step_node
    async def split(ctx: StepContext[str]) -> list[str]:
        return ctx.inputs.split()

    @g.step_node
    async def echo(ctx: StepContext[str]) -> str:
        ctx.emit(ctx.inputs)
        return ctx.inputs.upper()

    collect = g.collect_node(str, node_id="collect")
    g.add(
        g.edge_from(g.start_node).to(split),
        g.edge_from(split).map().to(echo),
        g.edge_from(echo).to(collect),
        g.edge_from(collect).to(g.end_node),
    )

    async def run() -> list[GraphEvent]:
        options = RunOptions(stream_node_data=True)
        return [event async for event in g.build().astream("a b c", state=None, deps=None, options=options)]

    events = asyncio.run(run())

    emitted = [e for e in events if isinstance(e, NodeEmitted)]
    assert all(e.node_id == "echo" for e in emitted)
    assert {e.data for e in emitted} == {"a", "b", "c"}
    # Each mapped item ran in its own branch, so every emission carries a distinct fork stack.
    assert len({e.fork_stack for e in emitted}) == 3


def test_StepContext_streaming_reflects_run_option() -> None:
    g = GraphBuilder(input_type=str, output_type=str, state_type=list)

    @g.step_node
    async def record(ctx: StepContext[str, list[bool]]) -> str:
        ctx.state.append(ctx.streaming)
        return ctx.inputs

    g.add(
        g.edge_from(g.start_node).to(record),
        g.edge_from(record).to(g.end_node),
    )
    graph = g.build()

    default_state: list[bool] = []
    graph.run("x", state=default_state, deps=None)

    streaming_state: list[bool] = []
    graph.run("x", state=streaming_state, deps=None, options=RunOptions(stream_node_data=True))

    # The flag mirrors stream_node_data: a node knows when its emitted data is observed.
    assert default_state == [False]
    assert streaming_state == [True]
