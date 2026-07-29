from __future__ import annotations

import json
import os
import re
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AliasChoices,
    AnyHttpUrl,
    Field,
    PostgresDsn,
    RedisDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_ENV_FILE = ".env"
ENV_FILE_VARIABLE = "AI_POLYPHITE_ENV_FILE"
LEGACY_ENV_FILE_VARIABLE = "PREDICTIONLAB_ENV_FILE"
_PROVIDER_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Validated runtime configuration.

    Source precedence is explicit constructor values, environment variables,
    dotenv values, then field defaults.
    """

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    service_name: str = Field(default="ai-polyphite-backend", min_length=1)
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO

    backend_host: str = "0.0.0.0"
    backend_port: int = Field(default=8000, ge=1, le=65535)

    database_url: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://predictionlab:predictionlab_local_only@127.0.0.1:5432/predictionlab"
    )
    redis_url: RedisDsn = RedisDsn("redis://127.0.0.1:6379/0")
    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")

    cors_allowed_origins: Annotated[tuple[AnyHttpUrl, ...], NoDecode] = (
        AnyHttpUrl("http://127.0.0.1:3000"),
        AnyHttpUrl("http://localhost:3000"),
    )
    cors_allow_credentials: bool = False
    readiness_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)
    enabled_providers: Annotated[tuple[str, ...], NoDecode] = Field(
        default=("mock",),
        validation_alias=AliasChoices(
            "enabled_providers",
            "AI_POLYPHITE_ENABLED_PROVIDERS",
        ),
    )
    collector_interval_seconds: float = Field(
        default=300,
        gt=0,
        le=86_400,
        validation_alias=AliasChoices(
            "collector_interval_seconds",
            "AI_POLYPHITE_COLLECTOR_INTERVAL_SECONDS",
        ),
    )
    provider_intervals_seconds: Annotated[dict[str, float], NoDecode] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "provider_intervals_seconds",
            "AI_POLYPHITE_PROVIDER_INTERVALS_SECONDS",
        ),
    )
    collector_run_immediately: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "collector_run_immediately",
            "AI_POLYPHITE_COLLECTOR_RUN_IMMEDIATELY",
        ),
    )
    collector_page_size: int = Field(
        default=500,
        ge=1,
        le=1_000,
        validation_alias=AliasChoices(
            "collector_page_size",
            "AI_POLYPHITE_COLLECTOR_PAGE_SIZE",
        ),
    )
    collector_max_pages_per_run: int = Field(
        default=100,
        ge=1,
        le=10_000,
        validation_alias=AliasChoices(
            "collector_max_pages_per_run",
            "AI_POLYPHITE_COLLECTOR_MAX_PAGES_PER_RUN",
        ),
    )
    manifold_sync_mode: Literal["catalog", "recent"] = Field(
        default="catalog",
        validation_alias=AliasChoices(
            "manifold_sync_mode",
            "AI_POLYPHITE_MANIFOLD_SYNC_MODE",
        ),
    )
    replay_dataset_directory: Path = Field(
        default=Path("backend/datasets/replay"),
        validation_alias=AliasChoices(
            "replay_dataset_directory",
            "AI_POLYPHITE_REPLAY_DATASET_DIRECTORY",
        ),
    )
    code_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "code_version",
            "AI_POLYPHITE_CODE_VERSION",
        ),
    )
    enable_manual_prediction_runs: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "enable_manual_prediction_runs",
            "AI_POLYPHITE_ENABLE_MANUAL_PREDICTION_RUNS",
        ),
    )
    replay_prediction_interval_hours: int = Field(
        default=24,
        ge=1,
        le=24 * 365,
        validation_alias=AliasChoices(
            "replay_prediction_interval_hours",
            "AI_POLYPHITE_REPLAY_PREDICTION_INTERVAL_HOURS",
        ),
    )
    prediction_minimum_confidence: Decimal = Field(
        default=Decimal("0.40"),
        ge=0,
        le=1,
    )
    prediction_maximum_disagreement: Decimal = Field(
        default=Decimal("0.30"),
        ge=0,
        le=1,
    )
    prediction_maximum_observation_age_seconds: int = Field(
        default=172_800,
        ge=1,
        le=31_536_000,
    )
    prediction_weak_edge: Decimal = Field(default=Decimal("0.03"), ge=0, le=1)
    prediction_moderate_edge: Decimal = Field(
        default=Decimal("0.08"),
        ge=0,
        le=1,
    )
    prediction_strong_edge: Decimal = Field(default=Decimal("0.15"), ge=0, le=1)
    enable_manual_paper_trading: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "enable_manual_paper_trading",
            "AI_POLYPHITE_ENABLE_MANUAL_PAPER_TRADING",
        ),
    )
    paper_currency_unit: Literal["USD_SIMULATED", "MANA_SIMULATED"] = (
        "USD_SIMULATED"
    )
    paper_initial_balance: Decimal = Field(default=Decimal("100"), gt=0)
    paper_entry_minimum_edge: Decimal = Field(
        default=Decimal("0.03"),
        ge=0,
        le=1,
    )
    paper_entry_minimum_confidence: Decimal = Field(
        default=Decimal("0.45"),
        ge=0,
        le=1,
    )
    paper_maximum_data_age_seconds: int = Field(
        default=172_800,
        ge=1,
        le=31_536_000,
    )
    paper_allow_yes: bool = True
    paper_allow_no: bool = True
    paper_minimum_stake: Decimal = Field(default=Decimal("0.50"), gt=0)
    paper_maximum_stake: Decimal = Field(default=Decimal("10.00"), gt=0)
    paper_sizing_policy: Literal["fixed_fraction", "confidence_adjusted"] = (
        "confidence_adjusted"
    )
    paper_base_equity_fraction: Decimal = Field(
        default=Decimal("0.01"),
        gt=0,
        le=1,
    )
    paper_maximum_market_fraction: Decimal = Field(
        default=Decimal("0.02"),
        gt=0,
        le=1,
    )
    paper_maximum_category_fraction: Decimal = Field(
        default=Decimal("0.15"),
        gt=0,
        le=1,
    )
    paper_maximum_total_exposure_fraction: Decimal = Field(
        default=Decimal("0.50"),
        gt=0,
        le=1,
    )
    paper_disagreement_reduction: Decimal = Field(
        default=Decimal("0.50"),
        ge=0,
        le=1,
    )
    paper_low_liquidity_reduction: Decimal = Field(
        default=Decimal("0.50"),
        ge=0,
        le=1,
    )
    paper_stale_data_reduction: Decimal = Field(
        default=Decimal("0.50"),
        ge=0,
        le=1,
    )
    paper_low_liquidity_threshold: Decimal = Field(default=Decimal("25"), ge=0)
    paper_sizing_stale_after_seconds: int = Field(
        default=86_400,
        ge=1,
        le=31_536_000,
    )
    paper_cost_model: Literal["zero", "conservative"] = "conservative"
    paper_percentage_fee: Decimal = Field(
        default=Decimal("0.005"),
        ge=0,
        le=1,
    )
    paper_fixed_fee: Decimal = Field(default=Decimal("0"), ge=0)
    paper_slippage_probability_points: Decimal = Field(
        default=Decimal("0.005"),
        ge=0,
        le=1,
    )
    paper_low_liquidity_penalty_points: Decimal = Field(
        default=Decimal("0.005"),
        ge=0,
        le=1,
    )
    paper_stale_observation_penalty_points: Decimal = Field(
        default=Decimal("0.005"),
        ge=0,
        le=1,
    )
    paper_evidence_preliminary_trades: int = Field(default=10, ge=1)
    paper_evidence_observation_trades: int = Field(default=30, ge=1)
    paper_evidence_expansion_trades: int = Field(default=100, ge=1)
    paper_evidence_maximum_concentration: Decimal = Field(
        default=Decimal("0.25"),
        ge=0,
        le=1,
    )
    paper_validation_interval_seconds: int = Field(
        default=3600,
        ge=60,
        le=86_400,
        validation_alias=AliasChoices(
            "paper_validation_interval_seconds",
            "AI_POLYPHITE_PAPER_VALIDATION_INTERVAL_SECONDS",
        ),
    )
    paper_validation_run_immediately: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "paper_validation_run_immediately",
            "AI_POLYPHITE_PAPER_VALIDATION_RUN_IMMEDIATELY",
        ),
    )
    paper_validation_portfolio_name: str = Field(
        default="MVP continuous validation",
        min_length=1,
        max_length=160,
        validation_alias=AliasChoices(
            "paper_validation_portfolio_name",
            "AI_POLYPHITE_PAPER_VALIDATION_PORTFOLIO_NAME",
        ),
    )
    paper_validation_random_seed: int = Field(
        default=17,
        ge=0,
        le=2_147_483_647,
        validation_alias=AliasChoices(
            "paper_validation_random_seed",
            "AI_POLYPHITE_PAPER_VALIDATION_RANDOM_SEED",
        ),
    )
    paper_validation_provider_codes: Annotated[tuple[str, ...], NoDecode] = Field(
        default=("manifold",),
        validation_alias=AliasChoices(
            "paper_validation_provider_codes",
            "AI_POLYPHITE_PAPER_VALIDATION_PROVIDER_CODES",
        ),
    )
    paper_validation_only_new_observations: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "paper_validation_only_new_observations",
            "AI_POLYPHITE_PAPER_VALIDATION_ONLY_NEW_OBSERVATIONS",
        ),
    )

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped:
            return ()

        if stripped.startswith("["):
            decoded = json.loads(stripped)
            if not isinstance(decoded, list):
                raise ValueError("CORS_ALLOWED_ORIGINS JSON value must be a list")
            return tuple(decoded)

        return tuple(origin.strip() for origin in stripped.split(",") if origin.strip())

    @field_validator(
        "enabled_providers",
        "paper_validation_provider_codes",
        mode="before",
    )
    @classmethod
    def parse_enabled_providers(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = tuple(part.strip().lower() for part in value.split(","))
        return value

    @field_validator("enabled_providers", "paper_validation_provider_codes")
    @classmethod
    def validate_enabled_providers(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not value:
            raise ValueError("At least one provider must be enabled.")
        normalized = tuple(code.strip().lower() for code in value)
        if any(not _PROVIDER_CODE_PATTERN.fullmatch(code) for code in normalized):
            raise ValueError("Enabled provider codes are invalid.")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Enabled provider codes must be unique.")
        return normalized

    @field_validator("provider_intervals_seconds", mode="before")
    @classmethod
    def parse_provider_intervals(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            return {}
        if stripped.startswith("{"):
            return json.loads(stripped)
        parsed: dict[str, float] = {}
        for entry in stripped.split(","):
            code, separator, seconds = entry.partition("=")
            if not separator:
                raise ValueError("Provider intervals must use code=seconds entries.")
            parsed[code.strip().lower()] = float(seconds)
        return parsed

    @field_validator("provider_intervals_seconds")
    @classmethod
    def validate_provider_intervals(
        cls,
        value: dict[str, float],
    ) -> dict[str, float]:
        for code, seconds in value.items():
            if not _PROVIDER_CODE_PATTERN.fullmatch(code):
                raise ValueError("Provider interval code is invalid.")
            if not 0 < seconds <= 86_400:
                raise ValueError("Provider intervals must be between 0 and 86400 seconds.")
        return value

    @model_validator(mode="after")
    def validate_prediction_thresholds(self) -> Settings:
        if not (
            self.prediction_weak_edge
            < self.prediction_moderate_edge
            < self.prediction_strong_edge
        ):
            raise ValueError("Prediction edge thresholds must be strictly increasing.")
        if self.paper_minimum_stake > self.paper_maximum_stake:
            raise ValueError("Paper minimum stake cannot exceed maximum stake.")
        if not (
            self.paper_evidence_preliminary_trades
            < self.paper_evidence_observation_trades
            < self.paper_evidence_expansion_trades
        ):
            raise ValueError(
                "Paper evidence thresholds must be strictly increasing."
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.cors_allowed_origins]

    def provider_interval(self, provider_code: str) -> float:
        return self.provider_intervals_seconds.get(
            provider_code,
            self.collector_interval_seconds,
        )

    def safe_summary(
        self,
    ) -> dict[
        str,
        str | int | float | bool | list[str] | dict[str, float],
    ]:
        """Return configuration fields that are safe to include in logs."""

        return {
            "service_name": self.service_name,
            "app_env": self.app_env.value,
            "log_level": self.log_level.value,
            "backend_host": self.backend_host,
            "backend_port": self.backend_port,
            "cors_allowed_origins": self.cors_origins,
            "cors_allow_credentials": self.cors_allow_credentials,
            "readiness_timeout_seconds": self.readiness_timeout_seconds,
            "enabled_providers": list(self.enabled_providers),
            "collector_interval_seconds": self.collector_interval_seconds,
            "provider_intervals_seconds": self.provider_intervals_seconds,
            "collector_run_immediately": self.collector_run_immediately,
            "collector_page_size": self.collector_page_size,
            "collector_max_pages_per_run": self.collector_max_pages_per_run,
            "manifold_sync_mode": self.manifold_sync_mode,
            "enable_manual_prediction_runs": self.enable_manual_prediction_runs,
            "enable_manual_paper_trading": self.enable_manual_paper_trading,
            "replay_prediction_interval_hours": self.replay_prediction_interval_hours,
            "paper_currency_unit": self.paper_currency_unit,
            "paper_initial_balance": str(self.paper_initial_balance),
            "paper_sizing_policy": self.paper_sizing_policy,
            "paper_cost_model": self.paper_cost_model,
            "paper_validation_interval_seconds": (
                self.paper_validation_interval_seconds
            ),
            "paper_validation_run_immediately": (
                self.paper_validation_run_immediately
            ),
            "paper_validation_portfolio_name": self.paper_validation_portfolio_name,
            "paper_validation_random_seed": self.paper_validation_random_seed,
            "paper_validation_provider_codes": list(
                self.paper_validation_provider_codes
            ),
            "paper_validation_only_new_observations": (
                self.paper_validation_only_new_observations
            ),
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    configured_env_file = os.getenv(
        ENV_FILE_VARIABLE,
        os.getenv(LEGACY_ENV_FILE_VARIABLE, DEFAULT_ENV_FILE),
    )
    env_file: str | Path | None = configured_env_file or None
    return Settings(_env_file=env_file)


def clear_settings_cache() -> None:
    """Clear cached settings for tests and controlled runtime reloads."""

    get_settings.cache_clear()
