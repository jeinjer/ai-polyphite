from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from predictionlab.api.app import create_app
from predictionlab.application.paper_trading import (
    ListPaperPortfolios,
    PaperPage,
    PaperPortfolioDetail,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.domain.paper_trading import (
    CurrencyUnit,
    PaperPortfolioStatus,
)

NOW = datetime(2026, 1, 2, tzinfo=UTC)
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000911")


def detail() -> PaperPortfolioDetail:
    return PaperPortfolioDetail(
        portfolio_id=PORTFOLIO_ID,
        name="API simulated portfolio",
        currency_unit=CurrencyUnit.USD_SIMULATED,
        initial_balance=Decimal("100"),
        cash_balance=Decimal("95"),
        reserved_balance=Decimal("5"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("1"),
        equity=Decimal("101"),
        total_exposure=Decimal("5"),
        status=PaperPortfolioStatus.ACTIVE,
        strategy_configuration_hash="a" * 64,
        experiment_run_id=None,
        created_at=NOW,
        updated_at=NOW,
    )


class StubPaperQueryService:
    def __init__(self) -> None:
        self.query: ListPaperPortfolios | None = None

    async def list_portfolios(
        self,
        query: ListPaperPortfolios,
    ) -> PaperPage[PaperPortfolioDetail]:
        self.query = query
        return PaperPage(
            items=(detail(),),
            page=query.page,
            page_size=query.page_size,
            total=1,
        )

    async def get_portfolio(self, portfolio_id: UUID) -> PaperPortfolioDetail:
        assert portfolio_id == PORTFOLIO_ID
        return detail()


def create_test_app():
    application = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TESTING,
            log_level=LogLevel.CRITICAL,
            enable_manual_paper_trading=False,
        )
    )
    application.state.paper_trading_query_service = StubPaperQueryService()
    application.state.paper_performance_service = SimpleNamespace()
    application.state.paper_trading_orchestrator = SimpleNamespace()
    return application


@pytest.mark.asyncio
async def test_paper_portfolio_routes_expose_read_model_and_filters() -> None:
    application = create_test_app()
    service = application.state.paper_trading_query_service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        listing = await client.get(
            "/paper-portfolios",
            params={
                "status": "active",
                "currency_unit": "USD_SIMULATED",
            },
        )
        item = await client.get(f"/paper-portfolios/{PORTFOLIO_ID}")

    assert listing.status_code == 200
    assert listing.json()["items"][0]["simulation_only"] is True
    assert listing.json()["items"][0]["equity"] == "101"
    assert item.status_code == 200
    assert service.query.status is PaperPortfolioStatus.ACTIVE
    assert service.query.currency_unit is CurrencyUnit.USD_SIMULATED


@pytest.mark.asyncio
async def test_manual_paper_controls_are_disabled_by_default() -> None:
    application = create_test_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/paper-trading/run",
            json={
                "portfolio_id": str(PORTFOLIO_ID),
                "prediction_run_id": "00000000-0000-4000-8000-000000000912",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Manual paper trading controls are disabled."


def test_openapi_documents_paper_trading_contract() -> None:
    paths = create_test_app().openapi()["paths"]

    assert "/paper-portfolios" in paths
    assert "/paper-portfolios/{portfolio_id}/performance" in paths
    assert "/paper-trades" in paths
    assert "/paper-positions" in paths
    assert "/trade-decisions" in paths
    assert "/paper-settlements" in paths
    assert "/experiment-runs/{experiment_id}/paper-performance" in paths
    assert "/paper-trading/run" in paths
