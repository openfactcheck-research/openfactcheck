"""Configuration — pydantic-settings with layered priority.

Resolution order (highest wins)::

    1. Constructor arguments
    2. Environment variables (``OPENFACTCHECK_`` prefix)
    3. ``.env`` file
    4. Config file (``openfactcheck.json`` or ``openfactcheck.yaml``)
    5. Field defaults
"""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class OpenFactCheckConfig(BaseSettings):
    """OpenFactCheck configuration.

    Reads from multiple sources automatically in priority order::

        # Just works — env vars + .env + config files + defaults
        config = OpenFactCheckConfig()

        # Programmatic overrides beat everything
        config = OpenFactCheckConfig(model="anthropic/claude-sonnet-4-6")

    Supported config files (looked up in working directory):

    - ``openfactcheck.json``
    - ``openfactcheck.yaml`` / ``openfactcheck.yml``

    Environment variables use the ``OPENFACTCHECK_`` prefix::

        OPENFACTCHECK_MODEL=gpt-4o-mini
        OPENFACTCHECK_VERBOSITY=debug
        SERPER_API_KEY=...
    """

    model_config = SettingsConfigDict(
        env_prefix="OPENFACTCHECK_",
        env_file=".env",
        env_file_encoding="utf-8",
        json_file="openfactcheck.json",
        json_file_encoding="utf-8",
        yaml_file=["openfactcheck.yaml", "openfactcheck.yml"],
        extra="ignore",
        case_sensitive=False,
    )

    model: str = "gpt-4o"
    verbosity: Literal["debug", "info", "warning", "error", "critical"] = "warning"
    prompts_dir: Path | None = None

    serper_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("SERPER_API_KEY", "OPENFACTCHECK_SERPER_API_KEY"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003 - required by pydantic-settings override.
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Priority: constructor > env vars > .env > json/yaml config > defaults."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            JsonConfigSettingsSource(settings_cls),
            YamlConfigSettingsSource(settings_cls),
        )
