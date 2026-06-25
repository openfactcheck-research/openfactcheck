"""Tests for the plug-in entry points: namespaces and pipelines resolve via metadata, lazily."""

import subprocess
import sys

from openfactcheck.components.registry import (
    get_component,
    get_pipeline,
    registered_namespaces,
    registered_pipelines,
)


def test_registered_namespaces_from_entry_points() -> None:
    """The component namespaces are discovered from entry-point metadata."""
    assert {"dummy", "factool", "factcheckgpt"} <= set(registered_namespaces())


def test_registered_pipelines_from_entry_points() -> None:
    """The prebuilt pipelines are discovered from entry-point metadata."""
    assert {"factool", "factcheckgpt", "rarr"} <= set(registered_pipelines())


def test_get_component_resolves_via_entry_point() -> None:
    """A component resolves through its namespace's entry point, carrying its role and default model."""
    component = get_component("factool/claim_processor")

    assert component.role == "claim_processor"
    assert component.default_model == "gpt-4o-mini"


def test_get_component_retriever_has_no_default_model() -> None:
    """A retriever makes no model calls, so it carries no default model."""
    assert get_component("factool/retriever").default_model is None


def test_get_component_reviser_is_in_the_pool() -> None:
    """The reviser is addressable in the flat pool, even though no prebuilt pipeline auto-wires it."""
    assert get_component("factcheckgpt/reviser").role == "reviser"


def test_get_pipeline_resolves_via_entry_point() -> None:
    """A prebuilt pipeline resolves through its entry point."""
    assert get_pipeline("factool").default_model == "gpt-4o-mini"


def test_import_openfactcheck_loads_no_namespaces() -> None:
    """Importing the library triggers zero namespace imports; a namespace loads only when selected."""
    script = (
        "import sys, openfactcheck\n"
        "loaded = [m for m in sys.modules if any(\n"
        "    p in m for p in ('components.factool', 'components.factcheckgpt', 'components.rarr',\n"
        "                     'components.dummy', 'nodes.factool', 'nodes.factcheckgpt', 'nodes.rarr')\n"
        ")]\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
