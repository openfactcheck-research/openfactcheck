"""Discovery of the components and prebuilt pipelines each namespace provides.

A component is addressed by a qualified ``"namespace/component"`` name (for example ``"factool/retriever"`` or
``"factcheckgpt/reviser"``); a prebuilt pipeline is addressed by its name (for example ``"factool"``).
Registration happens through two entry-point groups: ``openfactcheck.components`` (an entry's name is the
namespace, its value that namespace's set of named components) and ``openfactcheck.pipelines`` (an entry's name
is the pipeline, its value a [`Pipeline`][Pipeline]). The relevant module is imported only when one of its
components or its pipeline is first looked up, so importing the library, or selecting one, never loads the
others. Either may also be registered programmatically with [`register_components`][register_components] or
[`register_pipeline`][register_pipeline], which override an entry point of the same name.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Literal, cast

from openfactcheck.components.types import Input
from openfactcheck.graph import Graph

# ---------------------------------------------------------------------------
# Components: the flat namespace/component pool
# ---------------------------------------------------------------------------

_COMPONENT_GROUP = "openfactcheck.components"

type ComponentRole = Literal["claim_processor", "query_generator", "retriever", "verifier", "aggregator", "reviser"]
"""The pipeline role a component fills.

The linear pipeline uses it to place the component (extract, then per-claim query/retrieve/verify, then
aggregate, then revise); it is metadata, not the component's address.
"""


@dataclass(frozen=True, slots=True)
class Component:
    """A registered component: how to build it, the role it fills, and the model it defaults to.

    ``factory`` builds the component, an implementation of the protocol for its role. ``default_model`` is the
    model it uses unless one is configured; a component that makes no model calls (such as a retriever) leaves
    it ``None``.
    """

    factory: Callable[..., object]
    role: ComponentRole
    default_model: str | None = None


_component_overrides: dict[str, Mapping[str, Component]] = {}
_component_loaded: dict[str, Mapping[str, Component]] = {}


def register_components(namespace: str, components: Mapping[str, Component]) -> None:
    """Register a namespace's components, overriding any entry point of the same name.

    Args:
        namespace: The namespace that qualifies each component as ``namespace/component``.
        components: The namespace's components, keyed by their local name.
    """
    _component_overrides[namespace] = dict(components)


def get_component(name: str) -> Component:
    """Return the component for a qualified ``"namespace/component"`` name, importing its module on first lookup.

    Args:
        name: The qualified component name, ``"namespace/component"`` (for example ``"factool/retriever"``).

    Returns:
        The registered component.

    Raises:
        ValueError: If the name is not in ``"namespace/component"`` form, the namespace is unknown, or the
            namespace provides no component of that name.
        TypeError: If the namespace's entry point does not point to a mapping of [`Component`][Component].
    """
    namespace, separator, local = name.partition("/")
    if not separator or not local:
        raise ValueError(f"component name must be 'namespace/component'; got '{name}'.")
    components = _component_overrides[namespace] if namespace in _component_overrides else _load_namespace(namespace)
    if local not in components:
        available = ", ".join(sorted(components)) or "none"
        raise ValueError(f"namespace '{namespace}' provides no component '{local}'; it provides: {available}.")
    return components[local]


def registered_namespaces() -> tuple[str, ...]:
    """The names of every registered namespace, from entry points and programmatic registration."""
    return tuple(sorted({*_component_overrides, *(entry.name for entry in entry_points(group=_COMPONENT_GROUP))}))


def _load_namespace(namespace: str) -> Mapping[str, Component]:
    """Return a namespace's components, loading and caching its entry point on first lookup."""
    if namespace in _component_loaded:
        return _component_loaded[namespace]
    for entry in entry_points(group=_COMPONENT_GROUP):
        if entry.name == namespace:
            loaded = entry.load()
            if not isinstance(loaded, Mapping):
                raise TypeError(
                    f"entry point '{_COMPONENT_GROUP}' for '{namespace}' must point to a mapping of Component, "
                    f"got {type(loaded).__name__}."
                )
            mapping = cast("Mapping[str, Component]", loaded)
            _component_loaded[namespace] = mapping
            return mapping
    available = ", ".join(registered_namespaces()) or "none"
    raise ValueError(f"unknown namespace '{namespace}'; registered namespaces are: {available}.")


# ---------------------------------------------------------------------------
# Pipelines: the prebuilt pipelines
# ---------------------------------------------------------------------------

_PIPELINE_GROUP = "openfactcheck.pipelines"


@dataclass(frozen=True, slots=True)
class Pipeline:
    """A prebuilt pipeline: its graph builder and its default model.

    ``build_graph`` wires the graph from a chat client and an optional web-search client. ``default_model`` is
    the model it uses unless one is set globally.
    """

    build_graph: Callable[..., Graph[Input, Any, None, None]]
    default_model: str


_pipeline_overrides: dict[str, Pipeline] = {}
_pipeline_loaded: dict[str, Pipeline] = {}


def register_pipeline(name: str, pipeline: Pipeline) -> None:
    """Register a pipeline under ``name``, overriding any entry point of the same name.

    Args:
        name: The name the pipeline is selected by.
        pipeline: The pipeline's graph builder and default model.
    """
    _pipeline_overrides[name] = pipeline


def get_pipeline(name: str) -> Pipeline:
    """Return the pipeline registered under ``name``, importing its module on first lookup.

    Args:
        name: The pipeline name to look up.

    Returns:
        The registered pipeline.

    Raises:
        ValueError: If no pipeline is registered under ``name``.
        TypeError: If the entry point registered for ``name`` does not point to a [`Pipeline`][Pipeline].
    """
    return _pipeline_overrides[name] if name in _pipeline_overrides else _load_pipeline(name)


def registered_pipelines() -> tuple[str, ...]:
    """The names of every registered pipeline, from entry points and programmatic registration."""
    return tuple(sorted({*_pipeline_overrides, *(entry.name for entry in entry_points(group=_PIPELINE_GROUP))}))


def _load_pipeline(name: str) -> Pipeline:
    """Return a pipeline, loading and caching its entry point on first lookup."""
    if name in _pipeline_loaded:
        return _pipeline_loaded[name]
    for entry in entry_points(group=_PIPELINE_GROUP):
        if entry.name == name:
            loaded = entry.load()
            if not isinstance(loaded, Pipeline):
                raise TypeError(
                    f"entry point '{_PIPELINE_GROUP}' for '{name}' must point to a Pipeline, "
                    f"got {type(loaded).__name__}."
                )
            _pipeline_loaded[name] = loaded
            return loaded
    available = ", ".join(registered_pipelines()) or "none"
    raise ValueError(f"unknown pipeline '{name}'; registered pipelines are: {available}.")
