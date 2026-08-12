"""Periodic worker for continuous simulated validation."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from predictionlab.application.automation import AutomationState
from predictionlab.application.paper_validation import (
    PaperValidationRunFailedError,
    PaperValidationRunResult,
)
from predictionlab.core.clock import Clock, SystemClock

logger = logging.getLogger(__name__)
_MAX_WAIT_SLICE_SECONDS = 60.0


class PaperValidationRunner(Protocol):
    async def run_cycle(
        self,
        *,
        scheduled_for: datetime,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> PaperValidationRunResult: ...


class AutomationControlReader(Protocol):
    async def status(self) -> AutomationState: ...


class PaperValidationWorker:
    def __init__(
        self,
        *,
        runner: PaperValidationRunner,
        interval_seconds: int,
        run_immediately: bool,
        clock: Clock | None = None,
        automation_control: AutomationControlReader | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("paper validation interval must be positive")
        self._runner = runner
        self._interval_seconds = interval_seconds
        self._run_immediately = run_immediately
        self._clock = clock or SystemClock()
        self._automation_control = automation_control
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        logger.info(
            "paper_validation_worker_started",
            extra={
                "interval_seconds": self._interval_seconds,
                "simulation_only": True,
            },
        )
        try:
            if not self._run_immediately:
                first_slot = _scheduled_slot(
                    self._clock.now(),
                    self._interval_seconds,
                )
                if await self._wait_until(first_slot, next_slot=True):
                    return
            while not self._stop_event.is_set():
                scheduled_for = _scheduled_slot(
                    self._clock.now(),
                    self._interval_seconds,
                )
                await self._run_safely(
                    scheduled_for,
                    causation_id="paper-validation-interval",
                )
                if await self._wait_until(scheduled_for, next_slot=True):
                    return
        finally:
            logger.info(
                "paper_validation_worker_stopped",
                extra={"simulation_only": True},
            )

    async def run_once(
        self,
        *,
        scheduled_for: datetime | None = None,
    ) -> PaperValidationRunResult:
        resolved = scheduled_for or _scheduled_slot(
            self._clock.now(),
            self._interval_seconds,
        )
        return await self._runner.run_cycle(
            scheduled_for=resolved,
            correlation_id=f"manual-paper-validation-{uuid4()}",
            causation_id="paper-validation-once",
        )

    def stop(self) -> None:
        self._stop_event.set()

    async def _run_safely(
        self,
        scheduled_for: datetime,
        *,
        causation_id: str,
    ) -> None:
        if self._automation_control is not None:
            state = await self._automation_control.status()
            if state.paused:
                logger.warning(
                    "paper_validation_worker_paused",
                    extra={
                        "scheduled_for": scheduled_for.isoformat(),
                        "pause_reason": state.reason,
                        "simulation_only": True,
                    },
                )
                return
        try:
            await self._runner.run_cycle(
                scheduled_for=scheduled_for,
                correlation_id=f"worker-paper-validation-{uuid4()}",
                causation_id=causation_id,
            )
        except PaperValidationRunFailedError as exc:
            logger.error(
                "paper_validation_worker_cycle_failed",
                extra={
                    "run_id": str(exc.result.run_id),
                    "cycle_key": exc.result.cycle_key,
                    "safe_error_type": exc.result.safe_error_type,
                    "simulation_only": True,
                },
            )

    async def _wait_until(
        self,
        slot: datetime,
        *,
        next_slot: bool,
    ) -> bool:
        target_timestamp = slot.timestamp()
        if next_slot:
            target_timestamp += self._interval_seconds
        while not self._stop_event.is_set():
            delay = max(0.0, target_timestamp - self._clock.now().timestamp())
            if delay == 0:
                return False
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=min(delay, _MAX_WAIT_SLICE_SECONDS),
                )
            except TimeoutError:
                continue
            return True
        return True


def _scheduled_slot(value: datetime, interval_seconds: int) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("worker clock must return timezone-aware timestamps")
    utc_value = value.astimezone(UTC)
    epoch_seconds = int(utc_value.timestamp())
    scheduled_epoch = epoch_seconds - (epoch_seconds % interval_seconds)
    return datetime.fromtimestamp(scheduled_epoch, tz=UTC)
