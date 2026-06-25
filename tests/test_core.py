"""Tests for OpenFactCheck: the graph and prebuilt run modes."""

import os
from pathlib import Path

import pytest

from openfactcheck import OpenFactCheck, OpenFactCheckConfig
from openfactcheck.components.nodes import dummy
from openfactcheck.components.types import Input, Verdict
from openfactcheck.graph import Graph, GraphBuilder


@pytest.fixture(autouse=True)
def _clean_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate each test from ambient config: no OpenFactCheck env vars, a clean working directory."""
    for key in list(os.environ):
        if key.startswith("OPENFACTCHECK_") or key == "SERPER_API_KEY":
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


def _dummy_graph() -> Graph[Input, list[Verdict], None, None]:
    """A linear dummy pipeline that runs offline with no model or network calls."""
    g: GraphBuilder[Input, list[Verdict], None, None] = GraphBuilder(
        input_type=Input, output_type=list[Verdict], name="dummy"
    )
    cp = dummy.claim_processor(g)
    qg = dummy.query_generator(g)
    rt = dummy.retriever(g)
    vf = dummy.verifier(g)
    g.add(
        g.edge_from(g.start_node).to(cp),
        g.edge_from(cp).map().to(qg),
        g.edge_from(qg).to(rt),
        g.edge_from(rt).to(vf),
        g.edge_from(vf).collect().to(g.end_node),
    )
    return g.build()


def test_OpenFactCheck_run_graph_mode() -> None:
    """A directly-supplied graph runs offline and returns its output."""
    ofc = OpenFactCheck(graph=_dummy_graph())

    result = ofc.run("The earth is round.")

    assert isinstance(result, list)
    assert all(isinstance(verdict, Verdict) for verdict in result)


def test_OpenFactCheck_graph_overrides_config() -> None:
    """A graph wins over a configured pipeline: the dummy graph runs offline, the prebuilt is never built."""
    ofc = OpenFactCheck(OpenFactCheckConfig(pipeline="factool"), graph=_dummy_graph())

    result = ofc.run("The earth is round.")

    assert all(isinstance(verdict, Verdict) for verdict in result)


def test_OpenFactCheck_prebuilt_name_resolves_at_construction() -> None:
    """Naming a prebuilt pipeline resolves it at construction (no graph built yet, no keys needed)."""
    ofc = OpenFactCheck(OpenFactCheckConfig(pipeline="factool"))

    assert isinstance(ofc, OpenFactCheck)


def test_OpenFactCheck_unknown_pipeline_raises() -> None:
    """An unknown pipeline name fails at construction."""
    with pytest.raises(ValueError, match="unknown pipeline"):
        OpenFactCheck(OpenFactCheckConfig(pipeline="nope"))


def test_OpenFactCheck_nothing_to_run_raises() -> None:
    """No graph and no configured pipeline is an error."""
    with pytest.raises(ValueError, match="nothing to run"):
        OpenFactCheck(OpenFactCheckConfig())


def test_OpenFactCheck_stream_yields_events() -> None:
    """Streaming a run yields progress events."""
    ofc = OpenFactCheck(graph=_dummy_graph())

    events = list(ofc.stream("The earth is round."))

    assert events
