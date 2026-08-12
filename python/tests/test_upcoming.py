"""
Which games can be predicted right now.

Two rules are being checked. A game is only answerable once every earlier game of both its teams has
been collected, because a model would otherwise read a team one game out of date. And a game counts
as still to come until its tipoff, which is stored in UTC, rather than until a date compared against
the server's own clock. A rented server runs on UTC and a game's date is a United States eastern
date, so the second rule is the one that used to drop every game tipping off in the evening.
"""

from datetime import date, datetime, timedelta, timezone

from nba_ml import season, upcoming
from nba_ml.entities import Game, GameStatus, ScheduledGame
from nba_ml.stores import schedule, team_games, teams

import fake_data
from fake_data import PlayedGame

TOMORROW = season.today() + timedelta(days=1)
"""
The league's played games are a fixed season in the past, so a game still to come is dated from
today. Otherwise every one of them would be dropped for having already been played.
"""

def _store(games=fake_data.SEASON_GAMES, collected=None, scheduled=()):
    """
    Sets up one league: which games are on the schedule, and which of them have a box score.

    Args:
        games are on the schedule as finished games.
        collected are the games a box score was actually stored for, defaulting to all of them.
        scheduled are the games still to be played.
    """

    collected = games if collected is None else collected

    schedule.store([fake_data.scheduled_game(game) for game in games] + list(scheduled))

    if collected:
        team_games.store(fake_data.team_game_frame(collected))

def _upcoming(game_number: int, day: date, tipoff: datetime | None = None) -> ScheduledGame:
    """One game still to be played, between the first two teams unless a test says otherwise."""

    return ScheduledGame(
        id=fake_data.game_id(game_number),
        game=Game(day, 1, 2),
        status=GameStatus.SCHEDULED,
        tipoff=tipoff
    )

# THE COLLECTION RULE: #
def test_a_game_is_ready_once_both_teams_are_fully_collected():
    _store(scheduled=[_upcoming(20, TOMORROW)])

    games = upcoming.upcoming_games()

    assert [game.game.id for game in games] == [fake_data.game_id(20)]
    assert games[0].ready
    assert games[0].waiting_on is None

def test_a_game_waits_on_an_earlier_game_of_either_team_that_was_never_collected():
    """The last game of team 2 is played but never stored, so their next game cannot be answered."""

    missed = fake_data.SEASON_GAMES[-1]
    kept = [game for game in fake_data.SEASON_GAMES if game is not missed]

    _store(collected=kept, scheduled=[_upcoming(20, TOMORROW)])

    (game,) = upcoming.upcoming_games()

    assert not game.ready
    assert game.waiting_on == missed.day

def test_a_game_waits_on_the_teams_own_earlier_game_that_has_not_been_played():
    """Two games in a row for the same teams. Only the first of them can be answered."""

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

# THE TIPOFF RULE: #
def test_a_game_tipping_off_tonight_survives_a_server_that_has_already_rolled_over_to_tomorrow():
    """
    The bug this rule exists for.

    A game's date is its eastern date, and its tipoff can fall on the next day in UTC. Comparing that
    date against the server's own date therefore drops every game tipping off in the evening, from
    the moment UTC rolls over.
    """

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
    """Today's game is kept and yesterday's is not, both read in the eastern time zone."""

    _store(
        scheduled=[
            _upcoming(20, season.today()),
            _upcoming(21, season.today() - timedelta(days=1))
        ]
    )

    (game,) = upcoming.upcoming_games()

    assert game.game.id == fake_data.game_id(20)

def test_a_tipoff_stored_without_a_time_zone_is_read_as_utc():
    """Not every service publishes an offset, and the store holds the time in UTC either way."""

    naive_tipoff = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    _store(scheduled=[_upcoming(20, season.today(), naive_tipoff)])

    assert len(upcoming.upcoming_games()) == 1

# WHAT THE SERVICE OFFERS: #
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
    """A game against a team the pipeline holds nothing for is what a preseason exhibition looks like."""

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
