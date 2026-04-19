# Workspace

A pipeline configuration scoped to a project. Each workspace carries settings, a
content blob (the pipeline itself), and the latest run state.

## Data model/s

::: openfactcheck.api.models.workspace.Workspace
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.api.models.workspace.WorkspaceRun
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.api.models.workspace.WorkspaceRunStatus
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.api.models.workspace.WorkspaceSettings
    options:
      show_root_heading: true
      heading_level: 3

## Mutations

Payloads for creating and updating a workspace.

::: openfactcheck.api.models.workspace.WorkspaceCreate
    options:
      show_root_heading: true
      heading_level: 3

::: openfactcheck.api.models.workspace.WorkspaceUpdate
    options:
      show_root_heading: true
      heading_level: 3
