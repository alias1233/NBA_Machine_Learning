"""Tests for the hourly serving update command."""

from datetime import timedelta

from nba_ml import season
from nba_ml.cli import update_serving
from nba_ml.entities import GameStatus
from nba_ml.stores import rosters, schedule

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


def test_the_roster_window_reaches_the_games_the_site_is_about_to_be_asked_about(monkeypatch):
    tomorrow = fake_data.SEASON_GAMES[0]
    monkeypatch.setattr(season, "today", lambda: tomorrow.day - timedelta(days=1))
    schedule.store([fake_data.scheduled_game(tomorrow, status=GameStatus.SCHEDULED)])

    assert not update_serving.is_game_window()
    assert update_serving.is_roster_window()


def test_a_game_months_off_still_refreshes_the_rosters(monkeypatch):
    first = fake_data.SEASON_GAMES[0]
    monkeypatch.setattr(season, "today", lambda: first.day - timedelta(days=90))
    schedule.store([fake_data.scheduled_game(first, status=GameStatus.SCHEDULED)])

    assert not update_serving.is_game_window()
    assert update_serving.is_roster_window()


def test_a_schedule_with_nothing_left_to_play_wakes_nothing(monkeypatch):
    last = fake_data.SEASON_GAMES[-1]
    monkeypatch.setattr(season, "today", lambda: last.day + timedelta(days=2))
    schedule.store([fake_data.scheduled_game(last)])

    assert not update_serving.is_roster_window()


def test_the_hourly_job_refreshes_the_rosters_without_collecting_or_rebuilding(monkeypatch):
    source = fake_data.FakeSource(rosters=fake_data.roster_entries())
    monkeypatch.setattr(update_serving, "is_game_window", lambda: False)
    monkeypatch.setattr(update_serving, "is_roster_window", lambda: True)
    monkeypatch.setattr(update_serving.sources, "get_source", lambda: source)
    monkeypatch.setattr(
        update_serving.collect,
        "collect_all",
        lambda *arguments, **keywords: (_ for _ in ()).throw(AssertionError("Collection ran."))
    )

    update_serving.main()

    assert rosters.collected_at() is not None


def test_the_hourly_job_does_not_create_a_source_when_no_game_is_due(monkeypatch):
    monkeypatch.setattr(update_serving, "is_roster_window", lambda: False)
    monkeypatch.setattr(
        update_serving.sources,
        "get_source",
        lambda: (_ for _ in ()).throw(AssertionError("A source was created."))
    )

    update_serving.main()
