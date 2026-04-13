FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /usr/local/bin/uv

COPY pyproject.toml VERSION uv.lock LICENSE README.md ./
COPY src/ src/

RUN uv sync --frozen --no-dev --extra api

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "openfactcheck.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
