"""Block handlers — import all handler modules to auto-register them."""

import openfactcheck.engine.handlers.lists as lists  # noqa: F401
import openfactcheck.engine.handlers.logic as logic  # noqa: F401
import openfactcheck.engine.handlers.loops as loops  # noqa: F401
import openfactcheck.engine.handlers.math as math  # noqa: F401
import openfactcheck.engine.handlers.text as text  # noqa: F401
import openfactcheck.engine.handlers.variables as variables  # noqa: F401

__all__ = ["lists", "logic", "loops", "math", "text", "variables"]
