"""API server configuration loaded from OPENFACTCHECK_ prefixed environment variables."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class APIConfig(BaseSettings):
    """Configuration for the FastAPI server and all API subsystems."""

    model_config = SettingsConfigDict(env_prefix="OPENFACTCHECK_", env_file=".env")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3001"]

    # Auth
    auth_bypass: bool = False
    cognito_region: str = "us-east-1"
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""

    # Mode — "local" (SQLite, in-process execution) or "cloud" (DynamoDB, SQS)
    mode: Literal["local", "cloud"] = "local"
    sqlite_path: str = "~/.openfactcheck/data.db"
    dynamodb_table_name: str = "openfactcheck"
    dynamodb_region: str = "us-east-1"

    # Execution
    max_execution_timeout: int = 600
