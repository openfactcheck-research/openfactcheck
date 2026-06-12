"""Tests for the step-by-step driver: manual advance and recover-by-override."""

import asyncio

from openfactcheck.graph import GraphBuilder, StepContext


def test_GraphStepper_advance_reports_each_step() -> None:
    g = GraphBuilder[None, None, str, str]()

    @g.step_node
    async def upper(ctx: StepContext[None, None, str]) -> str:
        return ctx.inputs.upper()

    @g.step_node
    async def exclaim(ctx: StepContext[None, None, str]) -> str:
        return f"{ctx.inputs}!"

    g.add(
        g.edge_from(g.start_node).to(upper),
        g.edge_from(upper).to(exclaim),
        g.edge_from(exclaim).to(g.end_node),
    )
    graph = g.build()

    async def drive() -> tuple[list[str], str]:
        seen: list[str] = []
        async with graph.stepper("hi", state=None, deps=None) as run:
            while (step := await run.advance()) is not None:
                seen.append(step.node_id)
            return seen, run.output

    seen, output = asyncio.run(drive())

    assert seen == ["upper", "exclaim"]
    assert output == "HI!"


def test_GraphStepper_recover_overrides_failed_step() -> None:
    g = GraphBuilder[None, None, str, str]()

    @g.step_node
    async def boom(ctx: StepContext[None, None, str]) -> str:
        raise RuntimeError("nope")

    @g.step_node
    async def finish(ctx: StepContext[None, None, str]) -> str:
        return f"recovered:{ctx.inputs}"

    g.add(
        g.edge_from(g.start_node).to(boom),
        g.edge_from(boom).to(finish),
        g.edge_from(finish).to(g.end_node),
    )
    graph = g.build()

    async def drive() -> str:
        async with graph.stepper("x", state=None, deps=None) as run:
            while (step := await run.advance()) is not None:
                if step.error is not None:
                    run.recover(step, "fallback")
            return run.output

    assert asyncio.run(drive()) == "recovered:fallback"
