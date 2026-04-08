"""Health and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from openfactcheck import __version__

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning service identity."""
    return {
        "name": "OpenFactCheck API",
        "version": __version__,
        "status": "running",
    }


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
