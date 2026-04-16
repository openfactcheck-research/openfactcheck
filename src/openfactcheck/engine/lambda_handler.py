"""Lambda handler — executes a pipeline and returns the result.

Invoked by Step Functions. Receives pipeline JSON, returns execution output.
The engine is pure — no database access, no messaging, just compute.
"""

import asyncio
from typing import Any

from openfactcheck.engine.executor import execute_pipeline


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:  # noqa: ANN401 - AWS Lambda context type requires a heavy dependency.
    """AWS Lambda entry point — execute pipeline and return result."""
    pipeline: dict[str, Any] = event["pipeline"]
    result = asyncio.run(execute_pipeline(pipeline))
    return {
        "success": result.success,
        "output": result.output or "",
        "error": result.error or "",
    }
