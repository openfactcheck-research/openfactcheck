"""Tests for cycles: a converging loop, a bound-exceeded loop, and per-claim loops."""

from dataclasses import dataclass

import pytest

from openfactcheck.graph import GraphBuilder, GraphRuntimeError, StepContext


@dataclass
class _Ticks:
    """Counts how many times the loop body ran."""

    count: int = 0


def test_Graph_loop_converges() -> None:
    g = GraphBuilder[_Ticks, None, int, int]()

    @g.step_node
    async def tick(ctx: StepContext[_Ticks, None, int]) -> int:
        ctx.state.count += 1
        return ctx.inputs + 1

    @g.step_node
    async def finish(ctx: StepContext[_Ticks, None, int]) -> int:
        return ctx.inputs

    dec = g.decision_node(int, node_id="dec")
    g.add(
        g.edge_from(g.start_node).to(tick),
        g.edge_from(tick).to(dec),
        dec.when(lambda v: v < 5, tick, max_iterations=100),
        dec.otherwise(finish),
        g.edge_from(finish).to(g.end_node),
    )

    state = _Ticks()
    result = g.build().run(0, state=state, deps=None)

    assert result == 5
    assert state.count == 5


def test_Graph_loop_exceeds_bound() -> None:
    g = GraphBuilder[None, None, int, int]()

    @g.step_node
    async def tick(ctx: StepContext[None, None, int]) -> int:
        return ctx.inputs + 1

    @g.step_node
    async def finish(ctx: StepContext[None, None, int]) -> int:
        return ctx.inputs

    dec = g.decision_node(int, node_id="dec")
    g.add(
        g.edge_from(g.start_node).to(tick),
        g.edge_from(tick).to(dec),
        dec.when(lambda v: v < 1000, tick, max_iterations=3),
        dec.otherwise(finish),
        g.edge_from(finish).to(g.end_node),
    )

    with pytest.raises(GraphRuntimeError):
        g.build().run(0, state=None, deps=None)


def test_Graph_per_claim_loop_collects() -> None:
    g = GraphBuilder[None, None, list[int], list[int]]()

    @g.step_node
    async def fan(ctx: StepContext[None, None, list[int]]) -> list[int]:
        return ctx.inputs

    @g.step_node
    async def bump(ctx: StepContext[None, None, int]) -> int:
        return ctx.inputs + 1

    dec = g.decision_node(int, node_id="dec")
    collected = g.collect_node(int, node_id="collected")
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(bump),
        g.edge_from(bump).to(dec),
        dec.when(lambda v: v < 3, bump, max_iterations=10),
        dec.otherwise(collected),
        g.edge_from(collected).to(g.end_node),
    )

    result = g.build().run([0, 1, 2], state=None, deps=None)

    assert result == [3, 3, 3]
