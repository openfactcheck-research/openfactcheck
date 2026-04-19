# Errors

Exception hierarchy for the REST API. Middleware catches any subclass of
`AppError` and converts it to a JSON response with a matching HTTP status
and machine-readable error code.

::: openfactcheck.api.errors
