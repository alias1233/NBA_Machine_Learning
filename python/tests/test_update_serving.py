"""The server only collects and rebuilds around scheduled games."""

from datetime import timedelta

from nba_ml import season
from nba_ml.cli import update_serving
from nba_ml.stores import schedule

import fake_data


def test_the_hourly_job_skips_a_day_with_no_recent_scheduled_game(monkeypatch):
    today = fake_data.NEXT_GAME_DATE
    monkeypatch.setattr(season, "today", lambda: today)
    schedule.store([fake_data.scheduled_game(fake_data.SEASON_GAMES[0])])

    assert not update_serving.is_game_window()


def test_the_hourly_job_runs_for_a_game_from_yesterday(monkeypatch):
    today = fake_data.NEXT_GAME_DATE
    monkeypatch.setattr(season, "today", lambda: today)
    yesterday = fake_data.SEASON_GAMES[-1]
    schedule.store([fake_data.scheduled_game(yesterday)])

    assert yesterday.day == today - timedelta(days=3)
    assert not update_serving.is_game_window()

    monkeypatch.setattr(season, "today", lambda: yesterday.day + timedelta(days=1))

    assert update_serving.is_game_window()


def test_the_hourly_job_does_not_create_a_source_when_no_game_is_due(monkeypatch):
    monkeypatch.setattr(update_serving, "is_game_window", lambda: False)
    monkeypatch.setattr(
        update_serving.sources,
        "get_source",
        lambda: (_ for _ in ()).throw(AssertionError("A source was created."))
    )

    update_serving.main()
