"""Run a pipeline as an isolated subprocess.

Reads a Blockly workspace JSON on stdin and writes the execution result as
JSON on stdout. The process environment carries one user's secrets (set by the
caller), so each run is isolated from every other run in its own process.

    python -m openfactcheck.engine < pipeline.json
"""

import asyncio
import json
import sys

from openfactcheck.engine.executor import execute_pipeline


def main() -> None:
    """Execute the pipeline read from stdin and write the result to stdout."""
    pipeline = json.load(sys.stdin)
    result = asyncio.run(execute_pipeline(pipeline))
    json.dump(
        {"success": result.success, "output": result.output, "error": result.error or ""},
        sys.stdout,
    )


if __name__ == "__main__":
    main()
