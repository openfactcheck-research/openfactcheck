"""Tests for snapshot persistence and resume."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import BaseModel

from openfactcheck.graph import (
    FileStateStore,
    GraphBuilder,
    GraphPersistenceError,
    InMemoryStateStore,
    JoinSnapshot,
    RunOptions,
    RunSnapshot,
    RunStatus,
    StepContext,
    TaskSnapshot,
)
from openfactcheck.graph.forks import ForkStackItem


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


def _forked_snapshot(run_id: str) -> RunSnapshot:
    fork_stack = (ForkStackItem(fork_id="fork", fork_run_id="frun", branch_index=0),)
    return RunSnapshot(
        run_id=run_id,
        status=RunStatus.RUNNING,
        pending=(TaskSnapshot(node_id="worker", value="payload", fork_stack=fork_stack),),
        reducers={("join", "frun"): JoinSnapshot(downstream_stack=(), acc=1, count=2, items=[(0, "x")])},
        expected={"frun": 3},
        loops={("a", "b", fork_stack): 4},
        finalized=frozenset({("join", "frun")}),
        fork_seq=5,
        has_final=False,
        final=None,
        state=None,
    )


def test_FileStateStore_roundtrip_preserves_forked_state(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path)
    snapshot = _forked_snapshot("forked")

    asyncio.run(store.save(snapshot))
    loaded = asyncio.run(store.load("forked"))

    assert loaded == snapshot


def test_FileStateStore_persists_as_json(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path)
    graph = _three_step().build()

    graph.run("x", state=None, deps=None, options=RunOptions(store=store, run_id="j1"))

    raw = (tmp_path / "j1.json").read_bytes()
    assert json.loads(raw)


@pytest.mark.parametrize("run_id", ["..", ".", "../escape", "nested/id", "/absolute", "", "has space"])
def test_FileStateStore_rejects_unsafe_run_id(tmp_path: Path, run_id: str) -> None:
    store = FileStateStore(tmp_path)

    with pytest.raises(GraphPersistenceError):
        asyncio.run(store.history(run_id))


class _Doc(BaseModel):
    text: str


class _Counter(BaseModel):
    n: int


def _typed_graph() -> GraphBuilder[str, str, _Counter]:
    g = GraphBuilder(input_type=str, output_type=str, state_type=_Counter)

    @g.step_node
    async def make(ctx: StepContext[str, _Counter]) -> _Doc:
        return _Doc(text=ctx.inputs)

    @g.step_node
    async def use(ctx: StepContext[_Doc, _Counter]) -> str:
        # Attribute access only succeeds if the resumed value and state were
        # restored to their declared models rather than left as plain dicts.
        return f"{ctx.inputs.text}:{ctx.state.n}"

    g.add(
        g.edge_from(g.start_node).to(make),
        g.edge_from(make).to(use),
        g.edge_from(use).to(g.end_node),
    )
    return g


def test_Graph_resume_restores_declared_types(tmp_path: Path) -> None:
    store = FileStateStore(tmp_path)
    graph = _typed_graph().build()
    graph.run("x", state=_Counter(n=7), deps=None, options=RunOptions(store=store, run_id="full"))

    history = asyncio.run(store.history("full"))
    midrun = next(
        snapshot
        for snapshot in history
        if snapshot.status == RunStatus.RUNNING and any(task.node_id == "use" for task in snapshot.pending)
    )
    assert isinstance(midrun.state, dict)
    assert isinstance(midrun.pending[0].value, dict)

    resume_store = FileStateStore(tmp_path / "resumed")
    asyncio.run(resume_store.save(replace(midrun, run_id="resumed")))
    result = graph.resume("resumed", store=resume_store, deps=None)

    assert result == "x:7"
