"""Tests for snapshot persistence and resume."""

import asyncio
from dataclasses import replace
from pathlib import Path

from openfactcheck.graph import (
    FileStateStore,
    GraphBuilder,
    InMemoryStateStore,
    RunOptions,
    RunStatus,
    StepContext,
)


def _three_step() -> GraphBuilder[str, str]:
    g = GraphBuilder[str, str]()

    @g.step_node
    async def a(ctx: StepContext[str]) -> str:
        return ctx.inputs + "a"

    @g.step_node
    async def b(ctx: StepContext[str]) -> str:
        return ctx.inputs + "b"

    @g.step_node
    async def c(ctx: StepContext[str]) -> str:
        return ctx.inputs + "c"

    g.add(
        g.edge_from(g.start_node).to(a),
        g.edge_from(a).to(b),
        g.edge_from(b).to(c),
        g.edge_from(c).to(g.end_node),
    )
    return g


def test_Graph_run_saves_snapshots() -> None:
    store = InMemoryStateStore()
    graph = _three_step().build()

    result = graph.run("x", state=None, deps=None, options=RunOptions(store=store, run_id="r1"))

    assert result == "xabc"
    history = asyncio.run(store.history("r1"))
    assert [snapshot.status for snapshot in history][-1] == RunStatus.SUCCEEDED
    assert any(snapshot.status == RunStatus.RUNNING for snapshot in history)


def test_Graph_resume_from_midrun_snapshot() -> None:
    store = InMemoryStateStore()
    graph = _three_step().build()
    full = graph.run("x", state=None, deps=None, options=RunOptions(store=store, run_id="full"))

    history = asyncio.run(store.history("full"))
    midrun = next(snapshot for snapshot in history if snapshot.status == RunStatus.RUNNING)

    resume_store = InMemoryStateStore()
    asyncio.run(resume_store.save(replace(midrun, run_id="resume")))
    resumed = graph.resume("resume", store=resume_store, deps=None)

    assert resumed == full == "xabc"


def test_FileStateStore_roundtrip(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path)
    graph = _three_step().build()

    result = graph.run("x", state=None, deps=None, options=RunOptions(store=store, run_id="f1"))

    assert result == "xabc"
    latest = asyncio.run(store.load("f1"))
    assert latest is not None
    assert latest.status == RunStatus.SUCCEEDED
    assert latest.has_final
    assert latest.final == "xabc"
