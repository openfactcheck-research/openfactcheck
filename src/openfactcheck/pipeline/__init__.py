"""Ready-to-run fact-check pipelines, one per ported paper.

Each module here wires one paper's components onto its own fact-check graph and exposes a small pipeline
object with a ``run(text)`` surface that returns a [`Report`][openfactcheck.components.types.Report],
hiding the graph layer. There is no shared pipeline: every paper builds its own, so a method whose shape
differs from the others (an extra revision step, a research-and-revise loop) is expressed directly rather
than bent to fit a common template.

This layer is composition, not configuration: a pipeline takes already-built clients and components, not a
settings object. Resolving configuration into clients is the facade's concern, not the pipeline's.
"""

from openfactcheck.pipeline.factcheckgpt import FactcheckGPTPipeline, factcheckgpt
from openfactcheck.pipeline.factool import FactoolPipeline, factool

__all__ = [
    "FactcheckGPTPipeline",
    "FactoolPipeline",
    "factcheckgpt",
    "factool",
]
