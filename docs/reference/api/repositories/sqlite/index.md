# SQLite

Concrete SQLite-backed implementations of the API repositories. Each repository
is constructed from an async session factory and exposes the same async CRUD
surface as the DynamoDB backend.

- [Projects](projects.md) — `SqliteProjectRepository`.
- [Workspaces](workspaces.md) — `SqliteWorkspaceRepository`.
