"""
The cap on how many predictions run at once.

The service's memory ceiling is this and nothing else, because FastAPI gives every request its own
thread and runs as many as arrive. Two rules are being checked. A request over the cap waits and is
then refused honestly rather than being allowed to start, and the cap falls while no whole-league
build is published, since every request then builds the league for itself and holds gigabytes doing
it.
"""

import asyncio
from datetime import datetime

import pytest
from fastapi import HTTPException

from nba_ml.api import limits
from nba_ml.feature_engineering import feature_store
from nba_ml.models.player_stats import features as player_stat_features

def _slots(running: int = 2, waiting: int = 1, wait_seconds: float = 0.05) -> limits.PredictionSlots:
    return limits.PredictionSlots(running, waiting, wait_seconds)

def _publish_a_build():
    """The smallest thing that counts as a published whole-league build."""

    built_at = datetime.now()

    feature_store.publish(
        player_stat_features.BUILD_NAME,
        feature_store.FeatureBuild(
            version=built_at.strftime(feature_store.VERSION_FORMAT),
            built_at=built_at,
            window_start_date=None,
            sequence_columns=("POINTS",),
            subjects={1: feature_store.no_games(1)}
        )
    )

def _refusal(raised: HTTPException) -> dict:
    assert raised.status_code == 503
    assert raised.headers is not None and "Retry-After" in raised.headers

    return raised.detail

# THE CAP: #
def test_a_request_over_the_cap_waits_for_the_slot_it_needs():
    order: list[str] = []

    async def run():
        slots = _slots(running=1, waiting=1, wait_seconds=5)

        async def holder(name: str, hold_for: float):
            async with slots.hold():
                order.append(f"{name} in")
                await asyncio.sleep(hold_for)
                order.append(f"{name} out")

        await asyncio.gather(holder("first", 0.05), holder("second", 0))

    asyncio.run(run())

    assert order == ["first in", "first out", "second in", "second out"]

def test_a_request_arriving_with_the_queue_full_is_refused_rather_than_queued():
    async def run():
        slots = _slots(running=1, waiting=0, wait_seconds=5)

        async with slots.hold():
            with pytest.raises(HTTPException) as refused:
                async with slots.hold():
                    pass

            return _refusal(refused.value)

    detail = asyncio.run(run())

    assert detail["reason"] == limits.BUSY_REASON
    assert "the queue holds" in detail["message"]

def test_a_request_that_waits_too_long_is_refused():
    async def run():
        slots = _slots(running=1, waiting=4, wait_seconds=0.02)

        async with slots.hold():
            with pytest.raises(HTTPException) as refused:
                async with slots.hold():
                    pass

            return _refusal(refused.value)

    detail = asyncio.run(run())

    assert detail["reason"] == limits.BUSY_REASON
    assert "No slot came free" in detail["message"]

def test_a_slot_is_given_back_when_the_request_holding_it_fails():
    async def run():
        slots = _slots(running=1, waiting=0, wait_seconds=0.02)

        with pytest.raises(ZeroDivisionError):
            async with slots.hold():
                1 / 0

        # Nothing is holding the one slot, so this takes it rather than being refused.
        async with slots.hold():
            return True

    assert asyncio.run(run())

def test_a_ceiling_holds_back_a_request_that_the_cap_alone_would_let_through():
    """What a prediction with no published build asks for: fewer running than the service allows."""

    async def run():
        slots = _slots(running=4, waiting=0, wait_seconds=0.02)

        async with slots.hold(ceiling=1):
            with pytest.raises(HTTPException):
                async with slots.hold(ceiling=1):
                    pass

        # The lowered ceiling was the request's, not the service's, so the cap is what it was.
        async with slots.hold(), slots.hold():
            return True

    assert asyncio.run(run())

def test_a_ceiling_can_slow_the_service_down_but_never_stop_it_answering():
    async def run():
        slots = _slots(running=2, waiting=0, wait_seconds=0.02)

        async with slots.hold(ceiling=0):
            return True

    assert asyncio.run(run())

def test_a_cap_that_leaves_no_room_to_answer_is_refused():
    with pytest.raises(ValueError):
        _slots(running=0)

    with pytest.raises(ValueError):
        _slots(wait_seconds=0)

# WHAT THE SERVICE ASKS FOR: #
def test_fewer_run_together_while_no_whole_league_build_is_published():
    assert limits.running_ceiling() == limits.MAX_RUNNING_UNBUILT_PREDICTIONS

    _publish_a_build()

    assert limits.running_ceiling() == limits.MAX_RUNNING_PREDICTIONS

def test_asking_for_the_ceiling_never_reads_the_build():
    """
    It is asked on the event loop, so reading a build here would stop the service answering anything
    at all until the read finished. See api/limits.py.
    """

    _publish_a_build()
    feature_store._held.clear()

    limits.running_ceiling()

    assert feature_store._held == {}
