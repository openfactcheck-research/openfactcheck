"""Lambda handler — resolve the user's secrets and execute a pipeline in-process.

Invoked by Step Functions with the user id and the Blockly pipeline. The user's
API keys are decrypted from the secret store and placed in the environment only
for the duration of the run, then removed.

Isolation model: a Lambda execution environment handles one invocation at a
time (concurrency comes from more environments, never parallel invocations in
one process), so there is no race on the process environment. Each invocation
hard-resets the environment to the cold-start baseline plus that user's secrets
before running and restores the entry environment afterwards, so one run's keys
are never visible to another. User secrets may only add new variables; they
never override a baseline variable, so the function's own AWS and infrastructure
configuration cannot be shadowed by a user-named secret. Running in-process (vs.
a subprocess per run) lets a warm environment reuse the already-imported
provider SDKs, which is the bulk of the per-run cost.
"""

import asyncio
import os
from typing import Any

from openfactcheck.engine.executor import execute_pipeline
from openfactcheck.engine.secrets import resolve_user_secrets

# Environment captured at cold start, before any secret is ever injected. Every
# invocation runs against this baseline, so no secret can leak across runs.
_BASE_ENV = dict(os.environ)

# Wall-clock limit, kept under the Lambda timeout so a slow run returns a clean
# result instead of being killed mid-execution.
_RUN_TIMEOUT_SECONDS = 870


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:  # noqa: ANN401 - AWS Lambda context type requires a heavy dependency.
    """AWS Lambda entry point — execute the pipeline with the user's secrets."""
    user_id: str = event["user_id"]
    pipeline: dict[str, Any] = event["pipeline"]

    # Resolve secrets first, while the function's own AWS credentials are intact.
    secrets = resolve_user_secrets(user_id)
    # Only add new variables; a user secret never shadows a baseline variable.
    injectable = {name: value for name, value in secrets.items() if name not in _BASE_ENV}

    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(_BASE_ENV)
    os.environ.update(injectable)
    try:
        result = asyncio.run(asyncio.wait_for(execute_pipeline(pipeline), _RUN_TIMEOUT_SECONDS))
    except TimeoutError:
        return {"success": False, "output": "", "error": "Pipeline run timed out"}
    finally:
        os.environ.clear()
        os.environ.update(saved)

    return {
        "success": result.success,
        "output": result.output or "",
        "error": result.error or "",
    }
