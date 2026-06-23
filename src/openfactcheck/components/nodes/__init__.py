"""Prebuilt graph nodes that lift components onto the graph layer.

A node factory wraps a component as a graph [`Step`][openfactcheck.graph.Step], so a pipeline is composed by
wiring nodes with the graph API rather than hand-writing step functions. Each namespace builds its components
as nodes: the paper namespaces (`factool`, `factcheckgpt`, `rarr`) lift that paper's port, and `dummy` lifts
the deterministic placeholders for a no-dependency skeleton. Mix nodes from different namespaces in one graph.

Example:
    ```python
    from openfactcheck.components import nodes
    from openfactcheck.graph import GraphBuilder

    g = GraphBuilder(input_type=Input, output_type=list[Verdict])
    claim_processor = nodes.factcheckgpt.claim_processor(g, chat)  # FactcheckGPT's claim processor
    query_generator = nodes.rarr.query_generator(g, chat)  # RARR's question generation
    retriever = nodes.factool.retriever(g, serper)  # Factool's web retrieval
    verifier = nodes.factool.verifier(g, chat)  # Factool's verifier
    g.add(
        g.edge_from(g.start_node).to(claim_processor),
        g.edge_from(claim_processor).map().to(query_generator),
        g.edge_from(query_generator).to(retriever),
        g.edge_from(retriever).to(verifier),
        g.edge_from(verifier).collect().to(g.end_node),
    )
    ```
"""

from openfactcheck.components.nodes import dummy, factcheckgpt, factool, rarr

__all__ = [
    "dummy",
    "factcheckgpt",
    "factool",
    "rarr",
]
