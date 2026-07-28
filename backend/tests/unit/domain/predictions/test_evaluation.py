from decimal import Decimal

import pytest

from predictionlab.domain.predictions import (
    ConstantBaseline,
    MarketBaseline,
    score_probability,
)


def test_brier_log_loss_and_absolute_error() -> None:
    score = score_probability(Decimal("0.80"), Decimal("1"))

    assert score.brier_score == Decimal("0.04")
    assert score.absolute_error == Decimal("0.20")
    assert float(score.log_loss) == pytest.approx(0.2231435513)
    assert score.directionally_correct is True


def test_market_and_constant_baselines_are_explicit() -> None:
    market_probability = Decimal("0.63")

    assert MarketBaseline().probability(market_probability) == Decimal("0.63")
    assert ConstantBaseline().probability(market_probability) == Decimal("0.50")


def test_scoring_rejects_non_binary_outcomes() -> None:
    with pytest.raises(ValueError, match="binary"):
        score_probability(Decimal("0.60"), Decimal("0.50"))
