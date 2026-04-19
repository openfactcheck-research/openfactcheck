# Auth

Token verifiers for the REST API. Pluggable implementations of the same
verifier protocol; swap `CognitoVerifier` for `DevVerifier` in local
development or tests.

- [`TokenVerifier` protocol](protocol.md) — interface all verifiers implement.
- [`CognitoVerifier` class](cognito.md) — verifies Cognito ID tokens against a user pool's JWKS.
- [`DevVerifier` class](dev.md) — bypass verifier that returns the same user on every call.
