"""Middleware — error handling and CORS."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from openfactcheck.api.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)


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
    """Catch-all handler — prevents stack traces from leaking to clients."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "code": ErrorCode.INTERNAL_ERROR.value,
            "status": 500,
        },
    )


def register_middleware(app: FastAPI, cors_origins: list[str]) -> None:
    """Register all middleware and exception handlers on the app."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_error_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
