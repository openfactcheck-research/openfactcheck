"""Block handlers — import all handler modules to auto-register them."""

from openfactcheck.engine.handlers import (
    lists,
    logic,
    loops,
    math,
    text,
    variables,
)

__all__ = ["lists", "logic", "loops", "math", "text", "variables"]
