"""Boundary tests — integrations stay free of the fact-checking domain."""

from __future__ import annotations

import ast
from pathlib import Path

INTEGRATIONS_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "openfactcheck" / "integrations"

# Integrations are domain-agnostic service clients. They return service-shaped
# data; components (not integrations) map that into the fact-checking domain.
FORBIDDEN_PREFIXES = (
    "openfactcheck.components",
    "openfactcheck.pipeline",
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


def test_integrations_import_no_domain_modules() -> None:
    """No file under integrations/ imports a fact-checking domain module."""
    violations: list[str] = []

    for py_file in INTEGRATIONS_ROOT.rglob("*.py"):
        for lineno, module in _collect_imports(py_file):
            if module.startswith(FORBIDDEN_PREFIXES):
                rel = py_file.relative_to(INTEGRATIONS_ROOT)
                violations.append(f"{rel}:{lineno} imports '{module}'")

    assert violations == [], "integrations must stay domain-agnostic:\n" + "\n".join(violations)
