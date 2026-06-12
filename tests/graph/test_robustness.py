"""Tests for execution robustness: retry, timeouts, and the isolate error policy."""

import asyncio
from dataclasses import dataclass, field

import pytest

from openfactcheck.graph import GraphBuilder, RunOptions, StepContext


@dataclass
class _Attempts:
    """Records how many times a flaky step was attempted."""

    count: int = 0


def test_Graph_step_retries_until_success() -> None:
    g = GraphBuilder[_Attempts, None, str, str]()

    async def flaky(ctx: StepContext[_Attempts, None, str]) -> str:
        ctx.state.count += 1
        if ctx.state.count < 3:
            raise RuntimeError("transient")
        return ctx.inputs.upper()

    flaky_step = g.step_node(flaky, retries=5)
    g.add(
        g.edge_from(g.start_node).to(flaky_step),
        g.edge_from(flaky_step).to(g.end_node),
    )

    attempts = _Attempts()
    result = g.build().run("ok", state=attempts, deps=None)

    assert result == "OK"
    assert attempts.count == 3


def test_Graph_step_retries_exhausted_fails() -> None:
    g = GraphBuilder[None, None, str, str]()

    async def always_fails(ctx: StepContext[None, None, str]) -> str:
        raise RuntimeError("nope")

    step = g.step_node(always_fails, retries=2)
    g.add(
        g.edge_from(g.start_node).to(step),
        g.edge_from(step).to(g.end_node),
    )

    with pytest.raises(RuntimeError, match="nope"):
        g.build().run("x", state=None, deps=None)


def test_Graph_step_timeout_aborts() -> None:
    g = GraphBuilder[None, None, str, str]()

    async def slow(ctx: StepContext[None, None, str]) -> str:
        await asyncio.sleep(1.0)
        return ctx.inputs

    step = g.step_node(slow, timeout=0.02)
    g.add(
        g.edge_from(g.start_node).to(step),
        g.edge_from(step).to(g.end_node),
    )

    with pytest.raises(TimeoutError):
        g.build().run("x", state=None, deps=None)


@dataclass
class _Seen:
    """Collects which items a step processed."""

    items: list[int] = field(default_factory=list)


def test_Graph_isolate_drops_failed_branch() -> None:
    g = GraphBuilder[_Seen, None, list[int], list[int]]()

    @g.step_node
    async def fan(ctx: StepContext[_Seen, None, list[int]]) -> list[int]:
        return ctx.inputs

    @g.step_node
    async def doubled(ctx: StepContext[_Seen, None, int]) -> int:
        if ctx.inputs == 2:  # noqa: PLR2004 - the failing item under test.
            raise RuntimeError("bad item")
        return ctx.inputs * 2

    collected = g.collect_node(int, node_id="collected")
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(doubled),
        g.edge_from(doubled).to(collected),
        g.edge_from(collected).to(g.end_node),
    )

    result = g.build().run([1, 2, 3], state=_Seen(), deps=None, options=RunOptions(on_error="isolate"))

    assert sorted(result) == [2, 6]  # item 2 failed and was dropped; 1 -> 2, 3 -> 6


def test_Graph_isolate_all_branches_fail_collects_empty() -> None:
    g = GraphBuilder[None, None, list[int], list[int]]()

    @g.step_node
    async def fan(ctx: StepContext[None, None, list[int]]) -> list[int]:
        return ctx.inputs

    @g.step_node
    async def boom(ctx: StepContext[None, None, int]) -> int:
        raise RuntimeError("always")

    collected = g.collect_node(int, node_id="collected")
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(boom),
        g.edge_from(boom).to(collected),
        g.edge_from(collected).to(g.end_node),
    )

    result = g.build().run([1, 2, 3], state=None, deps=None, options=RunOptions(on_error="isolate"))

    assert result == []
