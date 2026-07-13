#!/bin/bash

# Startup script the Lambda Web Adapter runs as the function handler. It launches the API
# under uvicorn; the adapter proxies Function URL invocations to it and streams a run's
# newline-delimited events back as they happen (RESPONSE_STREAM).
PATH="$PATH:$LAMBDA_TASK_ROOT/bin" \
    PYTHONPATH="$PYTHONPATH:$LAMBDA_TASK_ROOT:/opt/python:$LAMBDA_RUNTIME_DIR" \
    exec python -m uvicorn --port="$PORT" openfactcheck.api.app:app
