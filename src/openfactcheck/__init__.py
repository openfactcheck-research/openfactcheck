"""OpenFactCheck: an open-source framework for fact-checking and factuality evaluation of LLMs."""

import importlib.metadata

from openfactcheck._core import OpenFactCheck
from openfactcheck.config import OpenFactCheckConfig

__all__ = [
    "OpenFactCheck",
    "OpenFactCheckConfig",
]

__version__ = importlib.metadata.version("openfactcheck")
