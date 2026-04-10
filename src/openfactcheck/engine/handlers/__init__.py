"""Block handlers — import all handler modules to auto-register them."""

import openfactcheck.engine.handlers.text as text  # noqa: F401

__all__ = ["text"]
