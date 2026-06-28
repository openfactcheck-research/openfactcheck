"""Block handlers — import all handler modules to auto-register them."""

from openfactcheck.engine.handlers import (
    io,
    lists,
    logic,
    loops,
    math,
    models,
    prompts,
    text,
    variables,
)

__all__ = ["io", "lists", "logic", "loops", "math", "models", "prompts", "text", "variables"]
