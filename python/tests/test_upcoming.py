"""Tests for finding the upcoming games that can be predicted."""

from datetime import date, datetime, timedelta, timezone

from nba_ml import season, upcoming
from nba_ml.entities import Game, GameStatus, ScheduledGame
from nba_ml.stores import schedule, team_games, teams

import fake_data
from fake_data import PlayedGame

TOMORROW = season.today() + timedelta(days=1)

def _store(games=fake_data.SEASON_GAMES, collected=None, scheduled=()):
    """Stores the schedule and the box scores of the collected games."""

    collected = games if collected is None else collected

    schedule.store([fake_data.scheduled_game(game) for game in games] + list(scheduled))

    if collected:
        team_games.store(fake_data.team_game_frame(collected))

def _upcoming(game_number: int, day: date, tipoff: datetime | None = None) -> ScheduledGame:
    """Returns a scheduled game between teams 1 and 2 that has not been played."""

    return ScheduledGame(
        id=fake_data.game_id(game_number),
        game=Game(day, 1, 2),
        status=GameStatus.SCHEDULED,
        tipoff=tipoff
    )

# COLLECTED GAMES: #
def test_a_game_is_ready_once_both_teams_are_fully_collected():
    _store(scheduled=[_upcoming(20, TOMORROW)])

    games = upcoming.upcoming_games()

    assert [game.game.id for game in games] == [fake_data.game_id(20)]
    assert games[0].ready
    assert games[0].waiting_on is None

def test_a_game_waits_on_an_earlier_game_of_either_team_that_was_never_collected():
    missed = fake_data.SEASON_GAMES[-1]
    kept = [game for game in fake_data.SEASON_GAMES if game is not missed]

    _store(collected=kept, scheduled=[_upcoming(20, TOMORROW)])

    (game,) = upcoming.upcoming_games()

    assert not game.ready
    assert game.waiting_on == missed.day

def test_a_game_waits_on_the_teams_own_earlier_game_that_has_not_been_played():
    _store(scheduled=[_upcoming(20, TOMORROW), _upcoming(21, TOMORROW + timedelta(days=2))])

    first, second = upcoming.upcoming_games()

    assert first.ready
    assert second.waiting_on == TOMORROW

def test_a_collected_game_is_no_longer_upcoming():
    played = PlayedGame(20, TOMORROW, 1, 2, 100, 99)

    _store(
        games=list(fake_data.SEASON_GAMES) + [played],
        scheduled=[fake_data.scheduled_game(played, status=GameStatus.SCHEDULED)]
    )

    assert upcoming.upcoming_games() == []

# TIPOFF TIMES: #
def test_a_game_tipping_off_tonight_survives_a_server_that_has_already_rolled_over_to_tomorrow():
    tipoff = datetime.now(timezone.utc) + timedelta(hours=1)
    yesterday_in_utc = datetime.now(timezone.utc).date() - timedelta(days=1)

    _store(scheduled=[_upcoming(20, yesterday_in_utc, tipoff)])

    (game,) = upcoming.upcoming_games()

    assert game.game.game.date == yesterday_in_utc
    assert game.ready

def test_a_game_that_has_already_tipped_off_is_not_upcoming():
    tipped_off = datetime.now(timezone.utc) - timedelta(hours=1)

    _store(scheduled=[_upcoming(20, season.today(), tipped_off)])

    assert upcoming.upcoming_games() == []

def test_a_game_with_no_published_tipoff_falls_back_to_its_eastern_date():
    _store(
        scheduled=[
            _upcoming(20, season.today()),
            _upcoming(21, season.today() - timedelta(days=1))
        ]
    )

    (game,) = upcoming.upcoming_games()

    assert game.game.id == fake_data.game_id(20)

def test_a_tipoff_stored_without_a_time_zone_is_read_as_utc():
    naive_tipoff = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    _store(scheduled=[_upcoming(20, season.today(), naive_tipoff)])

    assert len(upcoming.upcoming_games()) == 1

# PREDICTABLE GAMES: #
def test_until_keeps_the_answer_to_games_on_or_before_a_date():
    _store(
        scheduled=[
            _upcoming(20, TOMORROW),
            ScheduledGame(
                id=fake_data.game_id(21),
                game=Game(TOMORROW + timedelta(days=3), 3, 4),
                status=GameStatus.SCHEDULED
            )
        ]
    )

    kept = upcoming.upcoming_games(until=TOMORROW)

    assert [game.game.id for game in kept] == [fake_data.game_id(20)]

def test_only_ready_games_of_known_teams_can_be_predicted():
    against_an_unknown_team = ScheduledGame(
        id=fake_data.game_id(21),
        game=Game(TOMORROW, 3, 99),
        status=GameStatus.SCHEDULED
    )

    _store(scheduled=[_upcoming(20, TOMORROW), against_an_unknown_team])
    teams.store(fake_data.teams_frame())

    assert [game.id for game in upcoming.predictable_games()] == [fake_data.game_id(20)]
    assert len(upcoming.upcoming_games()) == 2

def test_nothing_is_upcoming_when_no_schedule_has_been_collected():
    assert upcoming.upcoming_games() == []
    assert upcoming.predictable_games() == []

def test_a_game_the_collection_rule_never_saw_is_left_for_the_next_call(monkeypatch):
    written_late = ScheduledGame(
        id=fake_data.game_id(21),
        game=Game(TOMORROW, 3, 4),
        status=GameStatus.SCHEDULED
    )

    _store(scheduled=[_upcoming(20, TOMORROW), written_late])

    seen_by_the_first_read = [
        row for row in schedule.team_game_dates() if row[0] != written_late.id
    ]
    monkeypatch.setattr(schedule, "team_game_dates", lambda: seen_by_the_first_read)

    assert [game.game.id for game in upcoming.upcoming_games()] == [fake_data.game_id(20)]
