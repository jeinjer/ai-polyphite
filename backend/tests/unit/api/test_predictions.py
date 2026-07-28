from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from predictionlab.api.app import create_app
from predictionlab.application.predictions import (
    AgentPredictionDetail,
    CalibrationBucket,
    ListPredictions,
    MetricSummary,
    PredictionEvaluationReport,
    PredictionRunDetail,
    PredictionRunPage,
)
from predictionlab.core.settings import AppEnvironment, LogLevel, Settings
from predictionlab.domain.agents import (
    AgentEvidence,
    EvidenceDirection,
    Recommendation,
)
from predictionlab.domain.predictions import OpportunityLevel, PredictionRunStatus

NOW = datetime(2026, 1, 2, tzinfo=UTC)
PREDICTION_ID = UUID("00000000-0000-4000-8000-000000000701")
MARKET_ID = UUID("00000000-0000-4000-8000-000000000702")
EXPERIMENT_ID = UUID("00000000-0000-4000-8000-000000000703")


def detail() -> PredictionRunDetail:
    agent = AgentPredictionDetail(
        agent_prediction_id=UUID("00000000-0000-4000-8000-000000000704"),
        agent_name="consensus",
        agent_version="1.0.0",
        predicted_probability=Decimal("0.64"),
        confidence=Decimal("0.60"),
        recommendation=Recommendation.YES,
        rationale_summary="Consenso ponderado.",
        evidence=(
            AgentEvidence(
                code="weighted_consensus",
                summary="Pesos trazables.",
                direction=EvidenceDirection.YES,
                strength=Decimal("0.4"),
            ),
        ),
        warnings=("No garantiza el resultado.",),
        input_hash="a" * 64,
        output_hash="b" * 64,
        duration_ms=Decimal("1.2"),
        disagreement_score=Decimal("0.08"),
        agent_weights={"market": Decimal("0.6"), "reasoning": Decimal("0.4")},
    )
    return PredictionRunDetail(
        prediction_run_id=PREDICTION_ID,
        experiment_run_id=EXPERIMENT_ID,
        market_id=MARKET_ID,
        market_title="Mercado de prueba",
        category="testing",
        predicted_at=NOW,
        market_probability=Decimal("0.52"),
        consensus_probability=Decimal("0.64"),
        consensus_confidence=Decimal("0.60"),
        recommendation=Recommendation.YES,
        edge=Decimal("0.12"),
        no_edge=Decimal("-0.12"),
        opportunity_level=OpportunityLevel.MODERATE,
        disagreement_score=Decimal("0.08"),
        status=PredictionRunStatus.COMPLETED,
        agent_configuration_hash="c" * 64,
        input_hash="d" * 64,
        result_hash="e" * 64,
        duration_ms=Decimal("4.5"),
        safe_error_type=None,
        abstention_reason=None,
        correlation_id="api-prediction",
        causation_id="test",
        created_at=NOW,
        agent_weights={"market": Decimal("0.6"), "reasoning": Decimal("0.4")},
        agent_predictions=(agent,),
    )


class StubPredictionQueryService:
    def __init__(self) -> None:
        self.query: ListPredictions | None = None

    async def list(self, query: ListPredictions) -> PredictionRunPage:
        self.query = query
        return PredictionRunPage(
            items=(detail(),),
            page=query.page,
            page_size=query.page_size,
            total=1,
        )

    async def get(self, prediction_id: UUID) -> PredictionRunDetail:
        assert prediction_id == PREDICTION_ID
        return detail()


class StubEvaluationService:
    async def evaluate(self, *, experiment_run_id: UUID | None):
        return PredictionEvaluationReport(
            experiment_run_id=experiment_run_id,
            resolved_count=1,
            emitted_count=1,
            abstained_count=0,
            coverage=Decimal("1"),
            system=MetricSummary(
                brier_score=Decimal("0.1"),
                log_loss=Decimal("0.2"),
                absolute_error=Decimal("0.3"),
                directional_accuracy=Decimal("1"),
            ),
            market_baseline=None,
            constant_baseline=None,
            calibration=(
                CalibrationBucket(
                    lower_bound=Decimal("0.6"),
                    upper_bound=Decimal("0.7"),
                    prediction_count=1,
                    mean_probability=Decimal("0.64"),
                    observed_frequency=Decimal("1"),
                ),
            ),
        )


def create_test_app(*, manual_enabled: bool = False):
    application = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TESTING,
            log_level=LogLevel.CRITICAL,
            enable_manual_prediction_runs=manual_enabled,
        )
    )
    application.state.prediction_query_service = StubPredictionQueryService()
    application.state.prediction_evaluation_service = StubEvaluationService()
    application.state.prediction_orchestrator = SimpleNamespace()
    return application


@pytest.mark.asyncio
async def test_prediction_routes_expose_filters_detail_and_evaluation() -> None:
    application = create_test_app()
    service = application.state.prediction_query_service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        listing = await client.get(
            "/predictions",
            params={
                "market_id": str(MARKET_ID),
                "recommendation": "yes",
                "status": "completed",
                "opportunity_level": "moderate",
                "experiment_run_id": str(EXPERIMENT_ID),
            },
        )
        prediction = await client.get(f"/predictions/{PREDICTION_ID}")
        market = await client.get(f"/markets/{MARKET_ID}/predictions")
        experiment = await client.get(
            f"/experiment-runs/{EXPERIMENT_ID}/predictions"
        )
        evaluation = await client.get(
            f"/experiment-runs/{EXPERIMENT_ID}/prediction-evaluation"
        )

    assert listing.status_code == 200
    assert listing.json()["items"][0]["edge"] == "0.12"
    assert prediction.json()["agent_predictions"][0]["agent_name"] == "consensus"
    assert market.status_code == 200
    assert experiment.status_code == 200
    assert evaluation.json()["system"]["brier_score"] == "0.1"
    assert service.query is not None


@pytest.mark.asyncio
async def test_manual_endpoint_is_disabled_by_default() -> None:
    application = create_test_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/predictions/run",
            json={"market_id": str(MARKET_ID), "predicted_at": NOW.isoformat()},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Manual prediction runs are disabled."


def test_openapi_documents_prediction_contract() -> None:
    paths = create_test_app().openapi()["paths"]

    assert "/predictions" in paths
    assert "/predictions/{prediction_id}" in paths
    assert "/markets/{market_id}/predictions" in paths
    assert "/experiment-runs/{experiment_id}/predictions" in paths
    assert "/predictions/run" in paths
