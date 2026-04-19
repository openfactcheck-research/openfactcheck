# Models

Pydantic domain models used by the REST API. Each module covers a concept
(project, workspace, user) along with its create and update payloads.

- [Project](project.md) — projects and their mutation payloads.
- [Workspace](workspace.md) — workspaces, pipeline run state, and settings.
- [User](user.md) — authenticated user extracted from a JWT.
