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
    ManualPaperTradeResult,
    ManualPaperTradeStatus,
    PaperPage,
    PaperPortfolioDetail,
    PaperTradingOutcome,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.domain.paper_trading import (
    CurrencyUnit,
    PaperPortfolioStatus,
    PositionSide,
    TradeDecision,
    TradeDecisionSource,
    TradeDecisionType,
)

NOW = datetime(2026, 1, 2, tzinfo=UTC)
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000911")
PREDICTION_ID = UUID("00000000-0000-4000-8000-000000000912")


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


class StubPaperOrchestrator:
    def __init__(self) -> None:
        self.command = None

    async def run_manual_override(self, command):
        self.command = command
        decision = TradeDecision(
            decision_id=UUID("00000000-0000-4000-8000-000000000913"),
            prediction_run_id=PREDICTION_ID,
            portfolio_id=PORTFOLIO_ID,
            decided_at=NOW,
            decision=TradeDecisionType.REJECTED,
            market_probability=Decimal("0.60"),
            system_probability=Decimal("0.70"),
            edge=Decimal("0.10"),
            confidence=Decimal("0.60"),
            opportunity_level="moderate",
            proposed_stake=Decimal("1"),
            approved_stake=Decimal("0"),
            rejection_reasons=("portfolio_inactive",),
            risk_checks=("manual_override:confirmed",),
            configuration_hash="b" * 64,
            result_hash="c" * 64,
            correlation_id="manual-api",
            causation_id=None,
            experiment_run_id=None,
            decision_source=TradeDecisionSource.MANUAL_OVERRIDE,
            override_reason=command.override_reason,
            idempotency_key=command.idempotency_key,
            side=command.side,
        )
        return ManualPaperTradeResult(
            ManualPaperTradeStatus.REJECTED,
            PaperTradingOutcome(decision, None, None, None),
        )


def create_test_app(
    *,
    override_enabled: bool = True,
    app_env: AppEnvironment = AppEnvironment.TESTING,
):
    application = create_app(
        Settings(
            _env_file=None,
            app_env=app_env,
            log_level=LogLevel.CRITICAL,
            enable_manual_paper_trading=False,
            enable_manual_paper_overrides=override_enabled,
        )
    )
    application.state.paper_trading_query_service = StubPaperQueryService()
    application.state.paper_performance_service = SimpleNamespace()
    application.state.paper_trading_orchestrator = StubPaperOrchestrator()
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


@pytest.mark.asyncio
async def test_manual_override_ignores_agent_decision_but_is_revalidated() -> None:
    application = create_test_app()
    orchestrator = application.state.paper_trading_orchestrator
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/paper-trading/manual-trades",
            json={
                "portfolio_id": str(PORTFOLIO_ID),
                "prediction_run_id": str(PREDICTION_ID),
                "side": "no",
                "requested_stake": "1.00",
                "override_reason": "Quiero operar igualmente.",
                "idempotency_key": "api-manual-1",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["decision_source"] == "manual_override"
    assert response.json()["side"] == "no"
    assert response.json()["simulation_only"] is True
    assert orchestrator.command.side is PositionSide.NO


@pytest.mark.asyncio
async def test_manual_override_is_structurally_blocked_in_production() -> None:
    application = create_test_app(app_env=AppEnvironment.PRODUCTION)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/paper-trading/manual-trades",
            json={
                "portfolio_id": str(PORTFOLIO_ID),
                "prediction_run_id": str(PREDICTION_ID),
                "side": "yes",
                "requested_stake": "1.00",
                "override_reason": "Debe permanecer simulado.",
                "idempotency_key": "api-manual-production",
            },
        )

    assert response.status_code == 403


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
    assert "/paper-trading/manual-trades" in paths
