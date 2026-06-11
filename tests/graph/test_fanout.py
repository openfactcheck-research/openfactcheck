"""Tests for per-item fan-out, count-based fan-in, and bounded concurrency."""

import asyncio
from dataclasses import dataclass

import pytest

from openfactcheck.graph import GraphBuilder, GraphBuildError, StepContext


def test_Graph_run_fanout_collects_in_source_order() -> None:
    g = GraphBuilder[None, None, str, list[str]]()

    @g.step
    async def split(ctx: StepContext[None, None, str]) -> list[str]:
        return ctx.inputs.split()

    @g.step
    async def shout(ctx: StepContext[None, None, str]) -> str:
        # First item sleeps longest, so completion order is the reverse of input order.
        await asyncio.sleep(0.01 if ctx.inputs == "a" else 0.0)
        return ctx.inputs.upper()

    collect = g.collect(str)
    g.add(
        g.edge_from(g.start_node).to(split),
        g.edge_from(split).map().to(shout),
        g.edge_from(shout).to(collect),
        g.edge_from(collect).to(g.end_node),
    )

    result = g.build().run("a b c", state=None, deps=None)

    assert result == ["A", "B", "C"]


def test_Graph_run_fanout_empty_collection() -> None:
    g = GraphBuilder[None, None, list[str], list[str]]()

    @g.step
    async def passthrough(ctx: StepContext[None, None, list[str]]) -> list[str]:
        return ctx.inputs

    @g.step
    async def shout(ctx: StepContext[None, None, str]) -> str:
        return ctx.inputs.upper()

    collect = g.collect(str)
    g.add(
        g.edge_from(g.start_node).to(passthrough),
        g.edge_from(passthrough).map().to(shout),
        g.edge_from(shout).to(collect),
        g.edge_from(collect).to(g.end_node),
    )

    result = g.build().run([], state=None, deps=None)

    assert result == []


@dataclass
class _Probe:
    """Counts concurrent step executions to verify the concurrency bound."""

    current: int = 0
    peak: int = 0


def test_Graph_arun_bounds_concurrency() -> None:
    g = GraphBuilder[_Probe, None, list[int], list[int]]()

    @g.step
    async def fan(ctx: StepContext[_Probe, None, list[int]]) -> list[int]:
        return ctx.inputs

    @g.step
    async def work(ctx: StepContext[_Probe, None, int]) -> int:
        ctx.state.current += 1
        ctx.state.peak = max(ctx.state.peak, ctx.state.current)
        await asyncio.sleep(0.01)
        ctx.state.current -= 1
        return ctx.inputs

    collect = g.collect(int)
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(work),
        g.edge_from(work).to(collect),
        g.edge_from(collect).to(g.end_node),
    )

    probe = _Probe()
    result = asyncio.run(g.build().arun([1, 2, 3, 4, 5], state=probe, deps=None, concurrency=2))

    assert sorted(result) == [1, 2, 3, 4, 5]
    assert probe.peak <= 2


def test_Graph_collect_duplicate_id() -> None:
    g = GraphBuilder[None, None, str, list[str]]()
    g.collect(str, node_id="dup")

    with pytest.raises(GraphBuildError):
        g.collect(str, node_id="dup")
