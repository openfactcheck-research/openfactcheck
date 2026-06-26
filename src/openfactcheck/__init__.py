"""OpenFactCheck: an open-source framework for fact-checking and factuality evaluation of LLMs."""

import importlib
from importlib.metadata import version
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openfactcheck._core import OpenFactCheck
    from openfactcheck.config import OpenFactCheckConfig

__all__ = [
    "OpenFactCheck",
    "OpenFactCheckConfig",
]

__version__ = version("openfactcheck")

# Re-export the facade lazily: importing the package, or any submodule such as the
# slim API, must not force-load the full library behind OpenFactCheck.
_EXPORTS = {
    "OpenFactCheck": "openfactcheck._core",
    "OpenFactCheckConfig": "openfactcheck.config",
}


def __getattr__(name: str) -> object:
    """Import a facade export on first access."""
    if (module := _EXPORTS.get(name)) is not None:
        return getattr(importlib.import_module(module), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
