"""Tests for fan-in reducers: sum, dict-merge, and first-wins early stop."""

import asyncio

from openfactcheck.graph import (
    GraphBuilder,
    StepContext,
    reduce_dict_update,
    reduce_first,
    reduce_sum,
)


def test_Graph_reduce_sum() -> None:
    g = GraphBuilder[list[int], float]()

    @g.step_node
    async def fan(ctx: StepContext[list[int]]) -> list[int]:
        return ctx.inputs

    @g.step_node
    async def square(ctx: StepContext[int]) -> int:
        return ctx.inputs * ctx.inputs

    total = g.reduce_node(reduce_sum, lambda: 0.0, item_type=int, node_id="total")
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(square),
        g.edge_from(square).to(total),
        g.edge_from(total).to(g.end_node),
    )

    result = g.build().run([1, 2, 3], state=None, deps=None)

    assert result == 14.0  # 1 + 4 + 9


def test_Graph_inline_reduce_sum() -> None:
    g = GraphBuilder[list[int], float]()

    @g.step_node
    async def fan(ctx: StepContext[list[int]]) -> list[int]:
        return ctx.inputs

    @g.step_node
    async def square(ctx: StepContext[int]) -> int:
        return ctx.inputs * ctx.inputs

    @g.step_node
    async def out(ctx: StepContext[float]) -> float:
        return ctx.inputs

    # .reduce() builds the fan-in join inline, with no reduce_node declared.
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(square),
        g.edge_from(square).reduce(reduce_sum, lambda: 0.0).to(out),
        g.edge_from(out).to(g.end_node),
    )

    result = g.build().run([1, 2, 3], state=None, deps=None)

    assert result == 14.0  # 1 + 4 + 9


def test_Graph_reduce_dict_update() -> None:
    g = GraphBuilder[list[str], dict[str, int]]()

    @g.step_node
    async def fan(ctx: StepContext[list[str]]) -> list[str]:
        return ctx.inputs

    @g.step_node
    async def measure(ctx: StepContext[str]) -> dict[str, int]:
        return {ctx.inputs: len(ctx.inputs)}

    merged = g.reduce_node(reduce_dict_update, dict, item_type=dict, node_id="merged")
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(measure),
        g.edge_from(measure).to(merged),
        g.edge_from(merged).to(g.end_node),
    )

    result = g.build().run(["a", "bb", "ccc"], state=None, deps=None)

    assert result == {"a": 1, "bb": 2, "ccc": 3}


def test_Graph_reduce_first_wins() -> None:
    g = GraphBuilder[list[int], int]()

    @g.step_node
    async def fan(ctx: StepContext[list[int]]) -> list[int]:
        return ctx.inputs

    @g.step_node
    async def slow_unless_ten(ctx: StepContext[int]) -> int:
        # Ten returns immediately; the others are delayed, so ten arrives first.
        await asyncio.sleep(0.0 if ctx.inputs == 10 else 0.05)
        return ctx.inputs

    first = g.reduce_node(reduce_first, lambda: None, item_type=int, node_id="first")
    g.add(
        g.edge_from(g.start_node).to(fan),
        g.edge_from(fan).map().to(slow_unless_ten),
        g.edge_from(slow_unless_ten).to(first),
        g.edge_from(first).to(g.end_node),
    )

    result = g.build().run([10, 20, 30], state=None, deps=None)

    assert result == 10
