"""Middleware: external host, error handling, and CORS."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from openfactcheck.api.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)


class ExternalHostMiddleware:
    """Rewrite the request ``Host`` to a fixed external host.

    Behind CloudFront and a Lambda Function URL the app sees the internal Function URL host (CloudFront
    must send the origin's host, and a Function URL rejects a foreign one), so any generated redirect,
    such as the trailing-slash redirect, would point off the public custom domain. Forcing the host to
    the external domain keeps redirects and absolute URLs on it.
    """

    def __init__(self, app: ASGIApp, host: str) -> None:
        """Wrap ``app``, rewriting the Host header of each HTTP request to ``host``."""
        self._app = app
        self._host = host.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Replace the request's Host header before passing it down the stack."""
        if scope["type"] == "http":
            scope = dict(scope)
            scope["headers"] = [(k, v) for k, v in scope["headers"] if k != b"host"] + [(b"host", self._host)]
        await self._app(scope, receive, send)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Convert AppError exceptions into structured JSON responses."""
    return JSONResponse(
        status_code=exc.status,
        content={
            "detail": exc.detail,
            "code": exc.code.value,
            "status": exc.status,
        },
    )


async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that prevents stack traces from leaking to clients."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "code": ErrorCode.INTERNAL_ERROR.value,
            "status": 500,
        },
    )


def register_middleware(app: FastAPI, cors_origins: list[str], external_host: str = "") -> None:
    """Register all middleware and exception handlers on the app."""
    app.add_exception_handler(AppError, app_error_handler)  # pyright: ignore[reportArgumentType] - Starlette handler type is broader than actual dispatch.
    app.add_exception_handler(Exception, generic_error_handler)  # pyright: ignore[reportArgumentType] - Starlette handler type is broader than actual dispatch.

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # Added last so it is outermost: the corrected host is in place before routing builds any redirect.
    if external_host:
        app.add_middleware(ExternalHostMiddleware, host=external_host)
