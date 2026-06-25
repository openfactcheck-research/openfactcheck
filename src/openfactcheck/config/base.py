"""The top-level configuration for a fact-checking run.

[`OpenFactCheckConfig`][OpenFactCheckConfig] holds global defaults (model, Serper credentials, runtime) and a
`pipeline` to run. It reads from several sources in priority order::

    1. Constructor arguments
    2. Environment variables (``OPENFACTCHECK_`` prefix)
    3. ``.env`` file
    4. Config file (``openfactcheck.json`` or ``openfactcheck.yaml``)
    5. Field defaults

Every field is a flat scalar, so any of them can come from the environment, the ``.env`` file, or a config
file.
"""

from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from openfactcheck.config.runtime import RuntimeSpec

type PipelineName = str
"""The name of a registered prebuilt pipeline, validated against the registry when the run is built."""


class OpenFactCheckConfig(BaseSettings):
    """OpenFactCheck configuration.

    Reads from several sources automatically in priority order::

        # Just works: env vars + .env + config files + defaults
        config = OpenFactCheckConfig()

        # Programmatic overrides beat everything
        config = OpenFactCheckConfig(model="anthropic/claude-sonnet-4-6")

    Supported config files (looked up in the working directory):

    - ``openfactcheck.json``
    - ``openfactcheck.yaml`` / ``openfactcheck.yml``

    Environment variables use the ``OPENFACTCHECK_`` prefix:

    ```bash
    OPENFACTCHECK_MODEL=anthropic/claude-sonnet-4-6
    OPENFACTCHECK_VERBOSITY=debug
    OPENFACTCHECK_PIPELINE=factool
    SERPER_API_KEY=...
    ```

    The `pipeline` names a prebuilt pipeline, resolved against the registry when the run is built. Build a
    custom pipeline in code and pass it as ``OpenFactCheck(graph=...)``.
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

    model: str | None = None
    """Global default model as ``"provider/model"``. Unset lets each component use its own default."""

    verbosity: Literal["debug", "info", "warning", "error", "critical"] = "warning"
    """Log level for a run."""

    serper_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("SERPER_API_KEY", "OPENFACTCHECK_SERPER_API_KEY"),
    )
    """Global Serper API key for web retrieval."""

    runtime: RuntimeSpec = RuntimeSpec()
    """Global runtime defaults applied to the pipeline's model calls."""

    pipeline: PipelineName | None = None
    """The prebuilt pipeline to run, by name. Build a custom pipeline in code and pass ``OpenFactCheck(graph=...)``."""

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
