"""Limits how many predictions run at the same time. Extra requests are queued or rejected."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from math import ceil

from fastapi import HTTPException

from nba_ml.feature_engineering import feature_store
from nba_ml.models.player_stats import features as player_stat_features

BUSY_REASON = "service_busy"
"""Reason code returned when the service is too busy."""

MAX_RUNNING_PREDICTIONS = int(os.environ.get("NBA_ML_MAX_RUNNING_PREDICTIONS", "4"))

MAX_RUNNING_UNBUILT_PREDICTIONS = int(os.environ.get("NBA_ML_MAX_RUNNING_UNBUILT_PREDICTIONS", "1"))
"""Max concurrent predictions when no feature build has been published."""

MAX_WAITING_PREDICTIONS = int(os.environ.get("NBA_ML_MAX_WAITING_PREDICTIONS", "8"))

MAX_WAIT_SECONDS = float(os.environ.get("NBA_ML_PREDICTION_WAIT_SECONDS", "10"))
"""Seconds a queued request waits for a slot before it is rejected."""

def running_ceiling() -> int:
    """Returns the current limit on concurrent predictions."""

    if not feature_store.is_published(player_stat_features.BUILD_NAME):
        return min(MAX_RUNNING_PREDICTIONS, MAX_RUNNING_UNBUILT_PREDICTIONS)

    return MAX_RUNNING_PREDICTIONS

class PredictionSlots:
    """Tracks running predictions and the requests waiting for a free slot."""

    def __init__(self, running: int, waiting: int, wait_seconds: float):
        if running < 1 or waiting < 0 or wait_seconds <= 0:
            raise ValueError(
                "A prediction cap needs at least one slot, a queue of nought or more, and a wait "
                f"above zero. Got {running}, {waiting}, {wait_seconds}."
            )

        self._room = asyncio.Condition()
        self._running = 0
        self._max_running = running
        self._waiting = 0
        self._max_waiting = waiting
        self._wait_seconds = wait_seconds

    @asynccontextmanager
    async def hold(self, ceiling: int | None = None) -> AsyncIterator[None]:
        """Takes a slot for the duration of the block, or raises a 503 if the service is full."""

        limit = self._max_running if ceiling is None else max(1, min(ceiling, self._max_running))

        await self._take(limit)

        try:
            yield
        finally:
            await self._give_back()

    async def _take(self, limit: int) -> None:
        async with self._room:
            if self._running >= limit and self._waiting >= self._max_waiting:
                raise self._busy(f"The cap of {limit} is full and the queue holds {self._waiting}.")

            self._waiting += 1

            try:
                async with asyncio.timeout(self._wait_seconds):
                    await self._room.wait_for(lambda: self._running < limit)
            except TimeoutError:
                raise self._busy(f"No slot came free within {self._wait_seconds:g} seconds.") from None
            finally:
                self._waiting -= 1

            self._running += 1

    async def _give_back(self) -> None:
        async with self._room:
            self._running -= 1
            # Waiters can have different limits, so notify all of them.
            self._room.notify_all()

    def _busy(self, detail: str) -> HTTPException:
        return HTTPException(
            503,
            detail={"reason": BUSY_REASON, "message": f"The service is busy. {detail}"},
            headers={"Retry-After": str(ceil(self._wait_seconds))}
        )

SLOTS = PredictionSlots(MAX_RUNNING_PREDICTIONS, MAX_WAITING_PREDICTIONS, MAX_WAIT_SECONDS)

async def prediction_slot() -> AsyncIterator[None]:
    """FastAPI dependency that limits concurrent predictions. Async so queued requests don't block a thread."""

    async with SLOTS.hold(running_ceiling()):
        yield
