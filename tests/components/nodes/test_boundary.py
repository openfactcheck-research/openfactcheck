"""Boundary tests — the nodes layer bridges components to the graph, but sits below pipelines."""

from __future__ import annotations

import ast
from pathlib import Path

NODES_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "src" / "openfactcheck" / "components" / "nodes"

# Nodes lift components onto the graph, so they may import components, graph, chat, and integrations.
# They must not import pipelines or the API: pipelines may later build on nodes, not the reverse.
FORBIDDEN_PREFIXES = (
    "openfactcheck.pipeline",
    "openfactcheck.api",
)


def _collect_imports(py_file: Path) -> list[tuple[int, str]]:
    """Return (line, module) for every import in the file."""
    imports: list[tuple[int, str]] = []
    tree = ast.parse(py_file.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.module))
        elif isinstance(node, ast.Import):
            imports.append((node.lineno, ".".join(alias.name for alias in node.names)))
    return imports


def test_nodes_layer_imports_no_pipeline_or_api() -> None:
    """No file under components/nodes/ imports a pipeline or the API."""
    violations: list[str] = []

    for py_file in NODES_ROOT.rglob("*.py"):
        for lineno, module in _collect_imports(py_file):
            if module.startswith(FORBIDDEN_PREFIXES):
                rel = py_file.relative_to(NODES_ROOT)
                violations.append(f"{rel}:{lineno} imports '{module}'")

    assert violations == [], "nodes layer must sit below pipelines:\n" + "\n".join(violations)
