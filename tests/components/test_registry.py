"""Tests for the registry: the flat paper/component pool and the prebuilt-pipeline pool."""

from collections.abc import Iterator

import pytest

from openfactcheck.components import registry
from openfactcheck.components.registry import (
    Component,
    Pipeline,
    get_component,
    get_pipeline,
    register_components,
    register_pipeline,
    registered_namespaces,
    registered_pipelines,
)


def _component(role: str = "retriever") -> Component:
    return Component(factory=lambda: None, role=role)  # type: ignore[arg-type]


def _pipeline(default_model: str = "openai/gpt-4o-mini") -> Pipeline:
    return Pipeline(build_graph=lambda **_: None, default_model=default_model)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _isolated_registry() -> Iterator[None]:
    """Keep each test's programmatic registrations from leaking into the others."""
    registry._component_overrides.clear()
    registry._component_loaded.clear()
    registry._pipeline_overrides.clear()
    registry._pipeline_loaded.clear()
    yield
    registry._component_overrides.clear()
    registry._component_loaded.clear()
    registry._pipeline_overrides.clear()
    registry._pipeline_loaded.clear()


# Components


def test_get_component_round_trips() -> None:
    """A registered component is returned by its qualified namespace/component name."""
    retriever = _component()
    register_components("ns", {"retriever": retriever})

    assert get_component("ns/retriever") is retriever


def test_get_component_requires_qualified_name() -> None:
    """A bare name without 'namespace/component' form is rejected."""
    with pytest.raises(ValueError, match="namespace/component"):
        get_component("factool")


def test_get_component_unknown_namespace_lists_namespaces() -> None:
    """An unknown namespace reports the registered ones."""
    register_components("ns", {"retriever": _component()})

    with pytest.raises(ValueError, match="unknown namespace 'missing'") as exc_info:
        get_component("missing/retriever")

    assert "ns" in str(exc_info.value)


def test_get_component_unknown_component_lists_what_it_provides() -> None:
    """A known namespace that lacks the component reports what it does provide."""
    register_components("ns", {"retriever": _component()})

    with pytest.raises(ValueError, match="provides no component 'verifier'") as exc_info:
        get_component("ns/verifier")

    assert "retriever" in str(exc_info.value)


def test_register_components_overrides_same_namespace() -> None:
    """Re-registering a namespace replaces its earlier components."""
    register_components("ns", {"retriever": _component()})
    replacement = _component()
    register_components("ns", {"retriever": replacement})

    assert get_component("ns/retriever") is replacement


def test_registered_namespaces_lists_sorted() -> None:
    """Registered namespaces are reported in sorted order."""
    register_components("zzz_ns", {"retriever": _component()})
    register_components("aaa_ns", {"retriever": _component()})

    namespaces = registered_namespaces()

    assert {"aaa_ns", "zzz_ns"} <= set(namespaces)
    assert list(namespaces) == sorted(namespaces)


def test_Component_default_model_is_optional() -> None:
    """A component that makes no model calls leaves default_model None."""
    assert Component(factory=lambda: None, role="retriever").default_model is None  # type: ignore[arg-type]


# Pipelines


def test_get_pipeline_round_trips() -> None:
    """A registered pipeline is returned by its name."""
    pipeline = _pipeline()
    register_pipeline("ns", pipeline)

    assert get_pipeline("ns") is pipeline


def test_get_pipeline_unknown_name_lists_pipelines() -> None:
    """An unknown pipeline reports the registered ones."""
    register_pipeline("ns", _pipeline())

    with pytest.raises(ValueError, match="unknown pipeline 'missing'") as exc_info:
        get_pipeline("missing")

    assert "ns" in str(exc_info.value)


def test_register_pipeline_overrides_same_name() -> None:
    """Re-registering a name replaces the earlier pipeline."""
    register_pipeline("ns", _pipeline())
    replacement = _pipeline()
    register_pipeline("ns", replacement)

    assert get_pipeline("ns") is replacement


def test_registered_pipelines_lists_sorted() -> None:
    """Registered pipelines are reported in sorted order."""
    register_pipeline("zzz_ns", _pipeline())
    register_pipeline("aaa_ns", _pipeline())

    pipelines = registered_pipelines()

    assert {"aaa_ns", "zzz_ns"} <= set(pipelines)
    assert list(pipelines) == sorted(pipelines)
