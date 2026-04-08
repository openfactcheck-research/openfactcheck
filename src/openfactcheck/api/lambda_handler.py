"""AWS Lambda handler — wraps the FastAPI app with Mangum."""

from __future__ import annotations

from mangum import Mangum

from openfactcheck.api.app import create_app

handler = Mangum(create_app())
