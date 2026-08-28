"""
How many predictions the service runs at once.

A prediction holds a few hundred megabytes while it runs, so how many run together is what decides
the service's memory ceiling. Nothing else bounds it: every endpoint is a plain `def`, so FastAPI
hands each request to a thread of its own and runs as many as arrive.

What a prediction holds depends on whether the whole-league feature build has been published. With
one, a request reads its player out of it. Without one, every request builds the league for itself,
which is measured in gigabytes rather than megabytes, so the cap is smaller while that is the state
the service is in. See running_ceiling.

A request over the cap waits for a slot, and it waits on the event loop rather than on a thread, so
queueing costs almost nothing. One that waits too long, or that arrives with the queue already full,
is refused with a Retry-After header saying when to come back. A burst is therefore a slow page and
then an honest refusal, never an out of memory kill.

Only the prediction routers are capped, so the cheap endpoints keep answering while every slot is
busy. That is what an uptime check on /health needs.

The numbers are environment variables, because the right ones depend on the server. They count per
process, so serving with more than one worker multiplies them.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from math import ceil

from fastapi import HTTPException

from nba_ml.feature_engineering import feature_store
from nba_ml.models.player_stats import features as player_stat_features

BUSY_REASON = "service_busy"
"""
The reason a refusal for a full service carries.

It travels the way the reasons in nba_ml/models/errors.py do, so a caller words a busy service for
its own reader instead of reading a status code. It is not one of them, because those are about the
stored data being unable to answer and this one is about the service being full.
"""

MAX_RUNNING_PREDICTIONS = int(os.environ.get("NBA_ML_MAX_RUNNING_PREDICTIONS", "4"))
"""How many predictions may run at once. Measured 2026-08-11: four together peaked at 0.45 GB."""

MAX_RUNNING_UNBUILT_PREDICTIONS = int(os.environ.get("NBA_ML_MAX_RUNNING_UNBUILT_PREDICTIONS", "1"))
"""
How many may run at once while no whole-league build is published. See running_ceiling.

Measured 2026-08-11: one request building the league for itself peaked at 1.7 GB, against 0.45 GB
for four reading a published build. The deployed container is capped at 2 GB, so one at a time is
what fits.
"""

MAX_WAITING_PREDICTIONS = int(os.environ.get("NBA_ML_MAX_WAITING_PREDICTIONS", "8"))
"""How many may queue for a slot. A request arriving past this is refused rather than queued."""

MAX_WAIT_SECONDS = float(os.environ.get("NBA_ML_PREDICTION_WAIT_SECONDS", "10"))
"""How long a queued request waits for a slot before it is refused."""

def running_ceiling() -> int:
    """
    How many predictions may run together right now.

    A published whole-league build is what makes a prediction cheap. Without one every player request
    builds the league for itself, which is the same work the build job does and holds gigabytes while
    it runs, so the ordinary cap would take the container past its memory limit and be killed. That
    is the state a server has before its first build job, and the one it has again if a build job
    fails for long enough that both kept versions go.

    Only whether a build exists is asked, never the build itself. This runs on the event loop rather
    than on a request's own thread, so reading one here would stop the service answering anything at
    all for as long as the read took. See feature_engineering/feature_store.py.
    """

    if not feature_store.is_published(player_stat_features.BUILD_NAME):
        return min(MAX_RUNNING_PREDICTIONS, MAX_RUNNING_UNBUILT_PREDICTIONS)

    return MAX_RUNNING_PREDICTIONS

class PredictionSlots:
    """
    The slots predictions run in, and the queue of requests waiting for one.

    One instance stands for the whole process, `SLOTS` below. It is a class so that a caller wanting
    different numbers, a test among them, can hold its own. Hold one per event loop: asyncio ties a
    condition to the loop it first waited on, and the service has exactly one loop.

    A caller names the ceiling it wants when it takes a slot, so the cap can fall while the service
    is in a state where a prediction costs more. Nothing already running is interrupted by a lower
    ceiling. It only stops the next request from starting until enough have finished.
    """

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
        """
        Holds one slot for as long as the caller needs it, or refuses to let the caller start.

        Args:
            ceiling is the most that may run together while this one does, for a request that costs
            more than usual. Never above the cap the service was built with, and never below one, so
            a ceiling can slow the service down but cannot stop it answering.
        """

        limit = self._max_running if ceiling is None else max(1, min(ceiling, self._max_running))

        await self._take(limit)

        try:
            yield
        finally:
            await self._give_back()

    async def _take(self, limit: int) -> None:
        async with self._room:
            # A free slot is taken whatever the queue holds, so a cap with no queue at all still serves.
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
            # Everyone waiting is woken rather than one of them, because they do not all hold the
            # same ceiling and the freed slot may only be enough for some of them.
            self._room.notify_all()

    def _busy(self, detail: str) -> HTTPException:
        return HTTPException(
            503,
            detail={"reason": BUSY_REASON, "message": f"The service is busy. {detail}"},
            headers={"Retry-After": str(ceil(self._wait_seconds))}
        )

SLOTS = PredictionSlots(MAX_RUNNING_PREDICTIONS, MAX_WAITING_PREDICTIONS, MAX_WAIT_SECONDS)

async def prediction_slot() -> AsyncIterator[None]:
    """
    Every prediction router is mounted with this, so a family is capped by being added.

    Being `async def` is what keeps a queued request off the thread pool. Only a request already
    holding a slot reaches the thread FastAPI runs a plain `def` endpoint on.
    """

    async with SLOTS.hold(running_ceiling()):
        yield
