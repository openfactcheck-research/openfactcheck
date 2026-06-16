# Graph

::: openfactcheck.graph
    options:
      members: false
      show_root_heading: false

## Pages

- [Builder](builder.md) — assemble and validate a graph from steps and edges.
- [Graph and execution](graph.md) — the runnable graph, run options, streaming, stepping, and resume.
- [Steps](step.md) — typed nodes, edges, and the per-invocation context.
- [Joins and reducers](join.md) — fan-in nodes and the reducers that combine branch outputs.
- [Decisions](decision.md) — conditional branching to one of several downstream paths.
- [Pause](pause.md) — suspend a run to await human input.
- [Events](events.md) — progress events emitted while a run executes.
- [Forks](forks.md) — fork-stack identity for fanned-out tasks.
- [Errors](errors.md) — the graph error hierarchy.
- [Persistence](persistence.md) — snapshot stores and resume.
- [Mermaid](mermaid.md) — render a graph as a diagram.
