"""Boundary tests — the graph engine stays generic (no domain imports)."""

from __future__ import annotations

import ast
from pathlib import Path

GRAPH_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "openfactcheck" / "graph"

# The graph engine is a generic orchestration substrate; it must not depend on
# the fact-checking domain. Pipelines that use the graph live outside this package.
FORBIDDEN_PREFIXES = (
    "openfactcheck.types",
    "openfactcheck.contracts",
    "openfactcheck.chat",
    "openfactcheck.prompts",
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


def test_graph_engine_imports_no_domain_modules() -> None:
    """No file under graph/ imports a fact-checking domain module."""
    violations: list[str] = []

    for py_file in GRAPH_ROOT.rglob("*.py"):
        for lineno, module in _collect_imports(py_file):
            if module.startswith(FORBIDDEN_PREFIXES):
                rel = py_file.relative_to(GRAPH_ROOT)
                violations.append(f"{rel}:{lineno} imports '{module}'")

    assert violations == [], "graph engine must stay generic:\n" + "\n".join(violations)
