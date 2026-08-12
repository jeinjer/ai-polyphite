from datetime import timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker

from predictionlab.core.settings import Settings
from predictionlab.domain.paper_trading import EntryContext, TradeDecisionType
from predictionlab.domain.predictions import OpportunityLevel, PredictionRunStatus
from predictionlab.runtime.paper_trading import create_paper_trading_orchestrator


def test_balanced_runtime_accepts_a_small_positive_edge_with_safe_confidence() -> None:
    orchestrator = create_paper_trading_orchestrator(
        session_factory=async_sessionmaker(),
        settings=Settings(_env_file=None),
    )

    assessment = orchestrator._entry_policy.evaluate(
        EntryContext(
            prediction_status=PredictionRunStatus.PREDICTED,
            market_is_open=True,
            market_probability=Decimal("0.50"),
            system_probability=Decimal("0.525"),
            yes_edge=Decimal("0.025"),
            confidence=Decimal("0.40"),
            opportunity_level=OpportunityLevel.NONE,
            data_age=timedelta(minutes=1),
            has_existing_position=False,
            data_complete=True,
        )
    )

    assert assessment.decision is TradeDecisionType.BUY_YES
    assert assessment.approved is True
