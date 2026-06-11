"""Boundary tests — enforce framework isolation inside chat/."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

CHAT_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "openfactcheck" / "chat"


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


@pytest.mark.parametrize(
    ("backend_name", "framework_prefixes"),
    [
        ("openai", ("openai",)),
        ("anthropic", ("anthropic",)),
    ],
)
def test_framework_imports_isolated_to_backend(backend_name: str, framework_prefixes: tuple[str, ...]) -> None:
    """Only files under backends/<name>/ may import from the framework modules."""
    allowed_dir = CHAT_ROOT / "backends" / backend_name
    violations: list[str] = []

    for py_file in CHAT_ROOT.rglob("*.py"):
        if allowed_dir in py_file.parents:
            continue
        for lineno, module in _collect_imports(py_file):
            if module.startswith(framework_prefixes):
                rel = py_file.relative_to(CHAT_ROOT)
                violations.append(f"{rel}:{lineno} imports '{module}'")

    assert violations == [], (
        f"{backend_name} framework imports found outside backends/{backend_name}/:\n" + "\n".join(violations)
    )
