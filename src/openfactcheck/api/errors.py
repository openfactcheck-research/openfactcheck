"""API error types and machine-readable error codes."""

from enum import StrEnum


class ErrorCode(StrEnum):
    """Machine-readable error codes returned in JSON error responses."""

    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROJECT_LIMIT_REACHED = "PROJECT_LIMIT_REACHED"
    WORKSPACE_LIMIT_REACHED = "WORKSPACE_LIMIT_REACHED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Base exception for all API errors.

    Caught by middleware and converted to a JSON response:

    ```json
    {
      "detail": "...",
      "code": "MACHINE_CODE",
      "status": 500
    }
    ```
    """

    def __init__(self, detail: str, code: ErrorCode, status: int = 500) -> None:
        """Create an error with the given detail, machine code, and HTTP status.

        Args:
            detail: Human-readable error message.
            code: Machine-readable error code for clients.
            status: HTTP status code.
        """
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status = status


class NotFoundError(AppError):
    """Raised when a requested resource does not exist (HTTP 404)."""

    def __init__(self, detail: str = "Resource not found") -> None:
        """Create the error, optionally with a custom detail message."""
        super().__init__(detail, ErrorCode.NOT_FOUND, status=404)


class AlreadyExistsError(AppError):
    """Raised when attempting to create a resource that already exists (HTTP 409)."""

    def __init__(self, detail: str = "Resource already exists") -> None:
        """Create the error, optionally with a custom detail message."""
        super().__init__(detail, ErrorCode.ALREADY_EXISTS, status=409)


class ProjectLimitError(AppError):
    """Raised when a user has reached their maximum project count (HTTP 422)."""

    def __init__(self, detail: str = "Project limit reached") -> None:
        """Create the error, optionally with a custom detail message."""
        super().__init__(detail, ErrorCode.PROJECT_LIMIT_REACHED, status=422)


class WorkspaceLimitError(AppError):
    """Raised when a project has reached its maximum workspace count (HTTP 422)."""

    def __init__(self, detail: str = "Workspace limit reached") -> None:
        """Create the error, optionally with a custom detail message."""
        super().__init__(detail, ErrorCode.WORKSPACE_LIMIT_REACHED, status=422)


class AuthError(AppError):
    """Raised when authentication fails or is missing (HTTP 401)."""

    def __init__(self, detail: str = "Authentication required") -> None:
        """Create the error, optionally with a custom detail message."""
        super().__init__(detail, ErrorCode.UNAUTHORIZED, status=401)


class ForbiddenError(AppError):
    """Raised when the user lacks permission for the requested action (HTTP 403)."""

    def __init__(self, detail: str = "Forbidden") -> None:
        """Create the error, optionally with a custom detail message."""
        super().__init__(detail, ErrorCode.FORBIDDEN, status=403)


class ExecutionTimeoutError(AppError):
    """Raised when pipeline execution exceeds the allowed timeout (HTTP 408)."""

    def __init__(self, detail: str = "Execution timed out") -> None:
        """Create the error, optionally with a custom detail message."""
        super().__init__(detail, ErrorCode.EXECUTION_TIMEOUT, status=408)


class ExecutionError(AppError):
    """Raised when pipeline execution fails (HTTP 500)."""

    def __init__(self, detail: str = "Execution failed") -> None:
        """Create the error, optionally with a custom detail message."""
        super().__init__(detail, ErrorCode.EXECUTION_ERROR, status=500)
