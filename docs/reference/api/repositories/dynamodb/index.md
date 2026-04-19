# DynamoDB

Concrete DynamoDB-backed implementations of the API repositories. Each repository
inherits from a shared single-table base and exposes the same async CRUD surface.

- [Base](base.md) — `BaseDynamoRepository`.
- [Projects](projects.md) — `DynamoProjectRepository`.
- [Workspaces](workspaces.md) — `DynamoWorkspaceRepository`.
