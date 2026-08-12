"""
How many predictions the service runs at once.

A prediction holds a few hundred megabytes while it runs, so how many run together is what decides
the service's memory ceiling. Nothing else bounds it: every endpoint is a plain `def`, so FastAPI
hands each request to a thread of its own and runs as many as arrive.

A request over the cap waits for a slot, and it waits on the event loop rather than on a thread, so
queueing costs almost nothing. One that waits too long, or that arrives with the queue already full,
is refused with a Retry-After header saying when to come back. A burst is therefore a slow page and
then an honest refusal, never an out of memory kill.

Only the prediction routers are capped, so the cheap endpoints keep answering while every slot is
busy. That is what an uptime check on /health needs.

The three numbers are environment variables, because the right ones depend on the server. They count
per process, so serving with more than one worker multiplies them.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from math import ceil

from fastapi import HTTPException

BUSY_REASON = "service_busy"
"""
The reason a refusal for a full service carries.

It travels the way the reasons in nba_ml/models/errors.py do, so a caller words a busy service for
its own reader instead of reading a status code. It is not one of them, because those are about the
stored data being unable to answer and this one is about the service being full.
"""

MAX_RUNNING_PREDICTIONS = int(os.environ.get("NBA_ML_MAX_RUNNING_PREDICTIONS", "4"))
"""How many predictions may run at once. Measured 2026-08-11: four together peaked at 0.45 GB."""

MAX_WAITING_PREDICTIONS = int(os.environ.get("NBA_ML_MAX_WAITING_PREDICTIONS", "8"))
"""How many may queue for a slot. A request arriving past this is refused rather than queued."""

MAX_WAIT_SECONDS = float(os.environ.get("NBA_ML_PREDICTION_WAIT_SECONDS", "10"))
"""How long a queued request waits for a slot before it is refused."""

class PredictionSlots:
    """
    The slots predictions run in, and the queue of requests waiting for one.

    One instance stands for the whole process, `SLOTS` below. It is a class so that a caller wanting
    different numbers, a test among them, can hold its own. Hold one per event loop: asyncio ties a
    queue to the loop it first waited on, and the service has exactly one loop.
    """

    def __init__(self, running: int, waiting: int, wait_seconds: float):
        if running < 1 or waiting < 0 or wait_seconds <= 0:
            raise ValueError(
                "A prediction cap needs at least one slot, a queue of nought or more, and a wait "
                f"above zero. Got {running}, {waiting}, {wait_seconds}."
            )

        self._free = asyncio.Semaphore(running)
        self._running = running
        self._waiting = 0
        self._max_waiting = waiting
        self._wait_seconds = wait_seconds

    @asynccontextmanager
    async def hold(self) -> AsyncIterator[None]:
        """Holds one slot for as long as the caller needs it, or refuses to let the caller start."""

        await self._take()

        try:
            yield
        finally:
            self._free.release()

    async def _take(self) -> None:
        # A free slot is taken whatever the queue holds, so a cap with no queue at all still serves.
        if self._free.locked() and self._waiting >= self._max_waiting:
            raise self._busy(
                f"The cap of {self._running} is full and the queue holds {self._waiting}."
            )

        self._waiting += 1

        try:
            async with asyncio.timeout(self._wait_seconds):
                await self._free.acquire()
        except TimeoutError:
            raise self._busy(f"No slot came free within {self._wait_seconds:g} seconds.") from None
        finally:
            self._waiting -= 1

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

    async with SLOTS.hold():
        yield
