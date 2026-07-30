from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from predictionlab.core.settings import (
    ENV_FILE_VARIABLE,
    AppEnvironment,
    LogLevel,
    Settings,
    clear_settings_cache,
    get_settings,
)
from predictionlab.providers.base import UnknownProviderError
from predictionlab.runtime.providers import create_configured_provider_registry


@pytest.fixture(autouse=True)
def reset_settings_cache() -> None:
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_settings_use_typed_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "SERVICE_NAME",
        "APP_ENV",
        "LOG_LEVEL",
        "BACKEND_PORT",
        "DATABASE_URL",
        "REDIS_URL",
        "CORS_ALLOWED_ORIGINS",
    ):
        monkeypatch.delenv(variable, raising=False)

    settings = Settings(_env_file=None)

    assert settings.service_name == "ai-polyphite-backend"
    assert settings.app_env is AppEnvironment.DEVELOPMENT
    assert settings.log_level is LogLevel.INFO
    assert settings.backend_port == 8000
    assert settings.cors_origins == [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
    assert settings.cors_allow_credentials is False


def test_settings_source_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / "test.env"
    env_file.write_text(
        "\n".join(
            [
                "SERVICE_NAME=from-file",
                "APP_ENV=production",
                "LOG_LEVEL=WARNING",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SERVICE_NAME", "from-environment")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.delenv("APP_ENV", raising=False)

    settings = Settings(
        _env_file=env_file,
        service_name="from-constructor",
    )

    assert settings.service_name == "from-constructor"
    assert settings.log_level is LogLevel.DEBUG
    assert settings.app_env is AppEnvironment.PRODUCTION


def test_get_settings_uses_configured_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / "custom.env"
    env_file.write_text("APP_ENV=testing\n", encoding="utf-8")
    monkeypatch.setenv(ENV_FILE_VARIABLE, str(env_file))

    settings = get_settings()

    assert settings.app_env is AppEnvironment.TESTING


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (
            "http://localhost:3000,https://dashboard.example.com",
            ["http://localhost:3000", "https://dashboard.example.com"],
        ),
        (
            '["http://localhost:3000", "https://dashboard.example.com"]',
            ["http://localhost:3000", "https://dashboard.example.com"],
        ),
    ],
)
def test_cors_origins_support_documented_formats(
    raw_value: str,
    expected: list[str],
) -> None:
    settings = Settings(
        _env_file=None,
        cors_allowed_origins=raw_value,
    )

    assert settings.cors_origins == expected


def test_invalid_runtime_configuration_fails_fast() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, backend_port=70_000)


def test_safe_summary_does_not_expose_connection_urls() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:secret@localhost:5432/database",
        redis_url="redis://:secret@localhost:6379/0",
    )

    summary = settings.safe_summary()

    assert "database_url" not in summary
    assert "redis_url" not in summary
    assert "secret" not in str(summary)


def test_provider_configuration_supports_global_and_per_source_intervals() -> None:
    settings = Settings(
        _env_file=None,
        enabled_providers="mock,manifold",
        collector_interval_seconds=300,
        provider_intervals_seconds="mock=10,manifold=120",
    )

    assert settings.enabled_providers == ("mock", "manifold")
    assert settings.provider_interval("mock") == 10
    assert settings.provider_interval("manifold") == 120
    assert settings.provider_interval("future_provider") == 300


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("enabled_providers", ""),
        ("enabled_providers", "mock,mock"),
        ("enabled_providers", "invalid provider"),
        ("provider_intervals_seconds", "mock=0"),
        ("provider_intervals_seconds", "invalid provider=10"),
    ],
)
def test_invalid_provider_configuration_fails_fast(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: value})


def test_runtime_rejects_unknown_enabled_provider_with_clear_error() -> None:
    settings = Settings(_env_file=None, enabled_providers="unknown")

    with pytest.raises(UnknownProviderError, match="Supported providers"):
        create_configured_provider_registry(settings)


def test_default_configuration_does_not_enable_a_real_provider() -> None:
    settings = Settings(_env_file=None)
    registry = create_configured_provider_registry(settings)

    assert registry.registered_codes == ("mock",)


def test_prediction_policy_is_configurable_and_validated() -> None:
    settings = Settings(
        _env_file=None,
        prediction_weak_edge="0.02",
        prediction_moderate_edge="0.07",
        prediction_strong_edge="0.12",
        prediction_minimum_confidence="0.35",
    )

    assert str(settings.prediction_weak_edge) == "0.02"
    assert str(settings.prediction_minimum_confidence) == "0.35"

    with pytest.raises(ValidationError, match="strictly increasing"):
        Settings(
            _env_file=None,
            prediction_weak_edge="0.08",
            prediction_moderate_edge="0.07",
            prediction_strong_edge="0.12",
        )


def test_paper_validation_runtime_configuration_is_typed() -> None:
    settings = Settings(
        _env_file=None,
        paper_validation_interval_seconds=900,
        paper_validation_run_immediately=False,
        paper_validation_portfolio_name="Frozen MVP",
        paper_validation_random_seed=42,
        paper_validation_provider_codes="manifold",
        paper_validation_only_new_observations=True,
        experimental_campaign_enabled=True,
        experimental_min_net_edge="0.015",
        enable_manual_paper_overrides=True,
    )

    assert settings.paper_validation_interval_seconds == 900
    assert settings.paper_validation_run_immediately is False
    assert settings.paper_validation_portfolio_name == "Frozen MVP"
    assert settings.paper_validation_random_seed == 42
    assert settings.paper_validation_provider_codes == ("manifold",)
    assert settings.paper_validation_only_new_observations is True
    assert settings.experimental_campaign_enabled is True
    assert settings.experimental_min_net_edge == Decimal("0.015")
    assert settings.enable_manual_paper_overrides is True

    with pytest.raises(ValidationError):
        Settings(_env_file=None, paper_validation_interval_seconds=30)
