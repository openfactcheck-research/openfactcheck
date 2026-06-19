"""Ready-to-run fact-check pipelines.

A [`Pipeline`][openfactcheck.pipeline.Pipeline] runs text through a fact-check graph and returns a
[`Report`][openfactcheck.components.types.Report], hiding the graph layer behind a
``run(text)`` surface. [`build_graph`][openfactcheck.pipeline.build_graph] is the default
claim-to-verdict topology, and [`Components`][openfactcheck.pipeline.Components] is the bag of components
that fill it. Established pipelines live in sibling modules (for example ``factool``), each a factory that
pairs a graph with a component family.

This layer is composition, not configuration: a pipeline takes already-built clients and components, not a
settings object. Resolving configuration into clients is the facade's concern, not the pipeline's.
"""

from openfactcheck.pipeline.pipeline import Components, Pipeline, PipelineState, build_graph

__all__ = [
    "Components",
    "Pipeline",
    "PipelineState",
    "build_graph",
]
