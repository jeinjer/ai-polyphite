"""Transactional orchestration for the initial four-agent prediction pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from time import perf_counter
from uuid import UUID, uuid4

from predictionlab.application.agents import PredictionAgent
from predictionlab.application.predictions.models import RunPrediction
from predictionlab.application.predictions.repository import (
    PredictionMarketRepository,
    PredictionUnitOfWork,
)
from predictionlab.core.clock import Clock, SystemClock
from predictionlab.core.hashing import canonical_sha256
from predictionlab.domain.agents import (
    AgentPrediction,
    JsonScalar,
    PredictionAgentInput,
    Recommendation,
)
from predictionlab.domain.predictions import (
    PredictionPolicy,
    PredictionRun,
    PredictionRunStatus,
)

logger = logging.getLogger(__name__)


class PredictionMarketNotFoundError(Exception):
    pass


class PredictionOrchestrator:
    def __init__(
        self,
        *,
        market_repository: PredictionMarketRepository,
        unit_of_work: Callable[[], PredictionUnitOfWork],
        reasoning_agent: PredictionAgent,
        market_agent: PredictionAgent,
        skeptic_agent: PredictionAgent,
        consensus_agent: PredictionAgent,
        policy: PredictionPolicy | None = None,
        clock: Clock | None = None,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._markets = market_repository
        self._unit_of_work = unit_of_work
        self._agents = (
            reasoning_agent,
            market_agent,
            skeptic_agent,
            consensus_agent,
        )
        self._policy = policy or PredictionPolicy()
        self._clock = clock or SystemClock()
        self._id_factory = id_factory

    def now(self) -> datetime:
        return self._clock.now()

    async def run(self, command: RunPrediction) -> PredictionRun:
        snapshot = await self._markets.get_as_of(
            command.market_id,
            command.predicted_at,
        )
        if snapshot is None:
            raise PredictionMarketNotFoundError(str(command.market_id))
        correlation_id = command.correlation_id or str(self._id_factory())
        configuration = self._configuration(command.model_configuration)
        configuration_hash = canonical_sha256(
            {
                "agents": tuple(
                    {"name": agent.name, "version": agent.version}
                    for agent in self._agents
                ),
                "model_configuration": configuration,
                "random_seed": command.random_seed,
            }
        )
        agent_input = PredictionAgentInput(
            market_id=snapshot.market_id,
            title=snapshot.title,
            description=snapshot.description,
            category=snapshot.category,
            status=snapshot.status,
            predicted_at=command.predicted_at,
            resolution_at=snapshot.resolution_at,
            market_probability=snapshot.latest_probability,
            observations=snapshot.observations,
            volume=snapshot.latest_volume,
            liquidity=snapshot.latest_liquidity,
            context=command.context,
            experiment_run_id=command.experiment_run_id,
            random_seed=command.random_seed,
            model_configuration=configuration,
        )
        started = perf_counter()
        logger.info(
            "prediction_run_started",
            extra={
                "market_id": str(command.market_id),
                "experiment_run_id": (
                    str(command.experiment_run_id)
                    if command.experiment_run_id is not None
                    else None
                ),
                "predicted_at": command.predicted_at.isoformat(),
                "agent_configuration_hash": configuration_hash,
                "correlation_id": correlation_id,
                "causation_id": command.causation_id,
            },
        )
        try:
            predictions: list[AgentPrediction] = []
            for agent in self._agents:
                current_input = replace(
                    agent_input,
                    prior_predictions=tuple(predictions),
                )
                predictions.append(await agent.predict(current_input))
            run = self._successful_run(
                command=command,
                correlation_id=correlation_id,
                configuration_hash=configuration_hash,
                agent_input=agent_input,
                predictions=tuple(predictions),
                duration_ms=_milliseconds(started),
            )
        except Exception as exc:
            logger.exception(
                "prediction_run_failed",
                extra={
                    "market_id": str(command.market_id),
                    "safe_error_type": type(exc).__name__,
                    "correlation_id": correlation_id,
                    "causation_id": command.causation_id,
                },
            )
            run = self._failed_run(
                command=command,
                correlation_id=correlation_id,
                configuration_hash=configuration_hash,
                input_hash=agent_input.input_hash,
                safe_error_type=type(exc).__name__,
                market_probability=agent_input.market_probability,
                duration_ms=_milliseconds(started),
            )
        persisted = await self._persist(run)
        logger.info(
            "prediction_run_finished",
            extra={
                "prediction_run_id": str(persisted.prediction_run_id),
                "market_id": str(command.market_id),
                "status": persisted.status.value,
                "recommendation": persisted.recommendation.value,
                "result_hash": persisted.result_hash,
                "duration_ms": str(persisted.duration_ms),
                "correlation_id": correlation_id,
                "causation_id": command.causation_id,
            },
        )
        return persisted

    async def run_batch(
        self,
        *,
        predicted_at: datetime,
        experiment_run_id: UUID | None,
        random_seed: int,
        context: dict[str, JsonScalar] | None = None,
        model_configuration: dict[str, JsonScalar] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> tuple[PredictionRun, ...]:
        market_ids = await self._markets.list_open_ids_as_of(predicted_at)
        return tuple(
            [
                await self.run(
                    RunPrediction(
                        market_id=market_id,
                        predicted_at=predicted_at,
                        experiment_run_id=experiment_run_id,
                        random_seed=random_seed,
                        context=context or {},
                        model_configuration=model_configuration or {},
                        correlation_id=correlation_id,
                        causation_id=causation_id,
                    )
                )
                for market_id in market_ids
            ]
        )

    def _configuration(
        self,
        overrides: Mapping[str, JsonScalar],
    ) -> dict[str, JsonScalar]:
        thresholds = self._policy.edge_thresholds
        configuration: dict[str, JsonScalar] = {
            "weak_edge": str(thresholds.weak),
            "moderate_edge": str(thresholds.moderate),
            "strong_edge": str(thresholds.strong),
            "minimum_confidence": str(self._policy.minimum_confidence),
            "maximum_disagreement": str(self._policy.maximum_disagreement),
            "maximum_observation_age_seconds": (
                self._policy.maximum_observation_age_seconds
            ),
            "extreme_probability_floor": str(self._policy.extreme_probability_floor),
            "extreme_probability_ceiling": str(
                self._policy.extreme_probability_ceiling
            ),
            "minimum_extreme_observations": (
                self._policy.minimum_extreme_observations
            ),
        }
        configuration.update(overrides)
        return configuration

    def _successful_run(
        self,
        *,
        command: RunPrediction,
        correlation_id: str,
        configuration_hash: str,
        agent_input: PredictionAgentInput,
        predictions: tuple[AgentPrediction, ...],
        duration_ms: Decimal,
    ) -> PredictionRun:
        consensus = predictions[-1]
        market_probability = agent_input.market_probability
        abstained = consensus.recommendation is Recommendation.ABSTAIN
        consensus_probability = None if abstained else consensus.predicted_probability
        edge = (
            consensus_probability - market_probability
            if consensus_probability is not None and market_probability is not None
            else None
        )
        status = (
            PredictionRunStatus.ABSTAINED
            if abstained
            else PredictionRunStatus.COMPLETED
        )
        result_hash = canonical_sha256(
            {
                "market_id": command.market_id,
                "predicted_at": command.predicted_at,
                "market_probability": market_probability,
                "consensus_probability": consensus_probability,
                "consensus_confidence": consensus.confidence,
                "recommendation": consensus.recommendation,
                "edge": edge,
                "disagreement_score": consensus.disagreement_score,
                "status": status,
                "configuration_hash": configuration_hash,
                "input_hash": agent_input.input_hash,
                "agent_output_hashes": tuple(item.output_hash for item in predictions),
            }
        )
        return PredictionRun(
            prediction_run_id=self._id_factory(),
            experiment_run_id=command.experiment_run_id,
            market_id=command.market_id,
            predicted_at=command.predicted_at,
            market_probability=market_probability,
            consensus_probability=consensus_probability,
            consensus_confidence=consensus.confidence,
            recommendation=consensus.recommendation,
            edge=edge,
            no_edge=-edge if edge is not None else None,
            opportunity_level=(
                self._policy.edge_thresholds.classify(edge)
                if edge is not None
                else self._policy.edge_thresholds.classify(Decimal("0"))
            ),
            disagreement_score=consensus.disagreement_score or Decimal("0"),
            status=status,
            agent_configuration_hash=configuration_hash,
            input_hash=agent_input.input_hash,
            result_hash=result_hash,
            duration_ms=duration_ms,
            safe_error_type=None,
            abstention_reason=consensus.rationale_summary if abstained else None,
            correlation_id=correlation_id,
            causation_id=command.causation_id,
            created_at=self._clock.now(),
            agent_weights=consensus.agent_weights,
            agent_predictions=predictions,
        )

    def _failed_run(
        self,
        *,
        command: RunPrediction,
        correlation_id: str,
        configuration_hash: str,
        input_hash: str,
        safe_error_type: str,
        market_probability: Decimal | None,
        duration_ms: Decimal,
    ) -> PredictionRun:
        result_hash = canonical_sha256(
            {
                "market_id": command.market_id,
                "predicted_at": command.predicted_at,
                "configuration_hash": configuration_hash,
                "input_hash": input_hash,
                "status": PredictionRunStatus.FAILED,
                "safe_error_type": safe_error_type,
            }
        )
        return PredictionRun(
            prediction_run_id=self._id_factory(),
            experiment_run_id=command.experiment_run_id,
            market_id=command.market_id,
            predicted_at=command.predicted_at,
            market_probability=market_probability,
            consensus_probability=None,
            consensus_confidence=Decimal("0"),
            recommendation=Recommendation.ABSTAIN,
            edge=None,
            no_edge=None,
            opportunity_level=self._policy.edge_thresholds.classify(Decimal("0")),
            disagreement_score=Decimal("0"),
            status=PredictionRunStatus.FAILED,
            agent_configuration_hash=configuration_hash,
            input_hash=input_hash,
            result_hash=result_hash,
            duration_ms=duration_ms,
            safe_error_type=safe_error_type,
            abstention_reason=None,
            correlation_id=correlation_id,
            causation_id=command.causation_id,
            created_at=self._clock.now(),
            agent_weights={},
            agent_predictions=(),
        )

    async def _persist(self, run: PredictionRun) -> PredictionRun:
        async with self._unit_of_work() as unit_of_work:
            persisted = await unit_of_work.predictions.save_if_absent(run)
            await unit_of_work.commit()
            return persisted


def _milliseconds(started: float) -> Decimal:
    return Decimal(str(round((perf_counter() - started) * 1_000, 3)))
