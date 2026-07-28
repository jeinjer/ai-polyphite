from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from predictionlab.infrastructure.database.repositories import (
    SqlAlchemyMarketObservationRepository,
    SqlAlchemyMarketRepository,
    SqlAlchemyMarketSnapshotRepository,
    SqlAlchemyMarketStateHistoryRepository,
    SqlAlchemyProviderRepository,
)


class SqlAlchemyMarketUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyMarketUnitOfWork:
        if self._session is not None:
            raise RuntimeError("unit of work is already active")
        self._session = self._session_factory()
        self.providers = SqlAlchemyProviderRepository(self._session)
        self.markets = SqlAlchemyMarketRepository(self._session)
        self.snapshots = SqlAlchemyMarketSnapshotRepository(self._session)
        self.observations = SqlAlchemyMarketObservationRepository(self._session)
        self.market_history = SqlAlchemyMarketStateHistoryRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        if self._session is None:
            return
        try:
            if exc_type is not None or self._session.in_transaction():
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        await self._active_session().commit()

    async def rollback(self) -> None:
        await self._active_session().rollback()

    def _active_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        return self._session
