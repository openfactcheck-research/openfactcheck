# Repositories

Data access layer for the REST API. Concrete implementations are backed by DynamoDB
in production and swappable for tests.

- [Protocols](protocols.md) — structural typing contracts every concrete repository satisfies.
- [Constants](constants.md) — shared limits and ID helpers used by every implementation.
- [DynamoDB](dynamodb/index.md) — DynamoDB-backed project and workspace repositories.
- [SQLite](sqlite/index.md) — SQLite-backed project and workspace repositories.
