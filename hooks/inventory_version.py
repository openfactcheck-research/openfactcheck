"""Inject the real openfactcheck version into the mkdocstrings inventory.

``mkdocstrings`` hardcodes ``inventory_version="0.0.0"`` at handler
construction time. This hook mutates ``plugin._handlers.inventory.version``
before ``_on_env_write_inventory`` (priority ``-20``) writes
``objects.inv``. Consumers on other sites can then rely on the inventory's
``# Version:`` header for cross-site linking.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Environment
    from mkdocs.config.defaults import MkDocsConfig


def _resolve_version() -> str:
    """Return the project version from package metadata, falling back to ``VERSION``."""
    try:
        return _pkg_version("openfactcheck")
    except PackageNotFoundError:
        return (Path(__file__).resolve().parents[2] / "VERSION").read_text().strip()


def on_env(env: Environment, /, *, config: MkDocsConfig, **_: Any) -> Environment:
    """Set the real project version on the mkdocstrings inventory before it is written."""
    plugin = config.plugins.get("mkdocstrings")
    if plugin is None:
        return env
    handlers = getattr(plugin, "_handlers", None)
    if handlers is None:
        return env
    handlers.inventory.version = _resolve_version()
    return env
