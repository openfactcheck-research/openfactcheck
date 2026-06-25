"""Configuration for fact-checking runs.

[`OpenFactCheckConfig`][OpenFactCheckConfig] is the layered settings object that drives a run; each stage's
model is written as a plain ``"provider/model"`` string in a [`ModelSpec`][ModelSpec] and resolved to a
provider configuration on demand.
"""

from openfactcheck.config.base import OpenFactCheckConfig, PipelineName
from openfactcheck.config.errors import ConfigError
from openfactcheck.config.models import ModelSpec
from openfactcheck.config.runtime import RuntimeSpec

# Settings
__all__ = [
    "OpenFactCheckConfig",
    "PipelineName",
]

# Specs
__all__ += [
    "ModelSpec",
    "RuntimeSpec",
]

# Errors
__all__ += [
    "ConfigError",
]
