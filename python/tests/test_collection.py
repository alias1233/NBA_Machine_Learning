"""
Collecting data into the stores, with a stand in service in place of the real one.

Nothing here reaches the network. The point is the part between the service and the store: which
seasons and dates get asked for, what lands in a table, what an update run does the second time it
is run, and what happens when the service refuses to answer. See tests/fake_data.py for the source.
"""

from datetime import date

from nba_ml.data_collection import games, players, schedule, teams
from nba_ml.entities import GameStatus
from nba_ml.season import SeasonType
from nba_ml.stores import (
    player_games,
    players as players_store,
    schedule as schedule_store,
    team_games,
    teams as teams_store
)

import fake_data
from fake_data import FakeSource, PlayedGame

ALL_ROWS = len(fake_data.SEASON_GAMES) * 2
"""Two team rows per game, which is what a full collection of the fake league writes."""

# TEAMS AND PLAYERS: #
def test_collecting_teams_fills_the_team_store():
    written = teams.collect(FakeSource(), print_debug=False)

    assert written == len(fake_data.TEAMS)
    assert teams_store.all_teams() == list(fake_data.TEAMS)
    assert teams_store.find("ANC") == fake_data.TEAMS[0]

def test_collecting_a_player_asks_the_service_once_per_player():
    source = FakeSource()

    written = players.collect(source, print_debug=False)

    assert written == len(fake_data.ALL_PLAYERS)
    assert players_store.stored_player_ids() == {player.id for player in fake_data.ALL_PLAYERS}
    assert source.requests.count("players") == 1
    assert sum(request.startswith("player_info") for request in source.requests) == len(fake_data.ALL_PLAYERS)

def test_only_the_players_that_are_missing_are_collected_again():
    source = FakeSource()
    first, second = fake_data.ALL_PLAYERS[0], fake_data.ALL_PLAYERS[1]

    players.collect(source, [first.id], print_debug=False)
    missing = players.missing_player_ids(source)

    assert first.id not in missing
    assert second.id in missing

    written = players.update(source, print_debug=False)

    assert written == len(fake_data.ALL_PLAYERS) - 1
    assert players_store.stored_player_ids() == {player.id for player in fake_data.ALL_PLAYERS}

def test_a_player_stored_without_a_name_is_named_from_the_service_player_list():
    """
    Not every service carries a name beside a player's other information, so collection fills it in
    from the list of players instead of asking again per player.
    """

    unnamed = fake_data.player_info_frame(fake_data.ALL_PLAYERS[:1]).drop(
        columns=[players_store.PLAYER_NAME.category_name]
    )
    players_store.store(unnamed)

    assert players_store.player_ids_without_names() == [fake_data.ALL_PLAYERS[0].id]

    named = players.fill_missing_names(FakeSource(), print_debug=False)

    assert named == 1
    assert players_store.get_player(fake_data.ALL_PLAYERS[0].id) == fake_data.ALL_PLAYERS[0]

def test_missing_career_years_are_derived_from_collected_games():
    player = fake_data.ALL_PLAYERS[0]
    player_games.store(fake_data.player_game_frame())
    source = FakeSource(known_players=[player])
    info = fake_data.player_info_frame([player]).assign(FROM_YEAR=None, TO_YEAR=None)
    source.player_info = lambda player_id: info.copy()

    players.collect(source, print_debug=False)

    stored = players_store.get_all_players_info().iloc[0]
    assert stored[players_store.FROM_YEAR.category_name] == fake_data.SEASON_YEAR
    assert stored[players_store.TO_YEAR.category_name] == fake_data.SEASON_YEAR

# BOX SCORES: #
def test_collecting_games_writes_both_stores():
    source = FakeSource()

    assert games.collect_team_games(source, print_debug=False) == ALL_ROWS
    assert games.collect_player_games(source, print_debug=False) == ALL_ROWS * fake_data.PLAYERS_PER_TEAM

    stored = team_games.get_all_team_game_data()

    assert len(stored) == ALL_ROWS
    assert team_games.latest_game_date() == fake_data.SEASON_GAMES[-1].day
    assert player_games.latest_game_date() == fake_data.SEASON_GAMES[-1].day
    assert team_games.stored_game_ids() == {game.id for game in fake_data.SEASON_GAMES}

def test_a_date_narrows_a_collection_run_to_the_games_inside_it():
    source = FakeSource()
    from_date = date(2024, 10, 30)

    written = games.collect_team_games(source, date_from=from_date, print_debug=False)

    stored = team_games.get_all_team_game_data()
    days = {row for row in stored[team_games.GAME_DATE.category_name]}

    assert written == len(stored)
    assert min(days) == "2024-10-30"

def test_collection_does_not_request_seasons_before_the_project_floor():
    source = FakeSource()
    source.oldest_season = 1946

    written = games.collect_team_games(
        source,
        seasons=[1984, fake_data.SEASON_YEAR],
        season_types=[SeasonType.REGULAR_SEASON],
        print_debug=False
    )

    assert written == ALL_ROWS
    assert all(f" {fake_data.SEASON_YEAR} " in request for request in source.requests)

def test_an_update_run_asks_only_for_what_is_newer_than_the_newest_game_stored():
    """
    This is what an hourly job runs, and it is the whole reason a run is cheap.

    The newest stored game is asked for again rather than skipped, because a game already stored is
    simply rewritten and a game played later the same day would otherwise be missed.
    """

    newest_collected = date(2024, 10, 25)
    still_to_come = [game for game in fake_data.SEASON_GAMES if game.day >= newest_collected]

    games.collect_team_games(FakeSource(), date_to=newest_collected, print_debug=False)

    updating = FakeSource()
    written = games.update_team_games(updating, print_debug=False)

    assert any(str(newest_collected) in request for request in updating.requests)
    assert written == len(still_to_come) * 2
    assert len(team_games.get_all_team_game_data()) == ALL_ROWS

def test_collecting_the_same_games_twice_rewrites_them_rather_than_duplicating_them():
    source = FakeSource()

    games.collect_team_games(source, print_debug=False)
    games.collect_team_games(source, print_debug=False)

    assert len(team_games.get_all_team_game_data()) == ALL_ROWS

def test_a_season_the_service_refuses_is_skipped_and_the_rest_of_the_run_carries_on():
    """A long run must not be lost to one season the service will not answer for."""

    source = FakeSource(failing_seasons=[fake_data.SEASON_YEAR - 1])

    written = games.collect_team_games(
        source,
        seasons=[fake_data.SEASON_YEAR - 1, fake_data.SEASON_YEAR],
        season_types=[SeasonType.REGULAR_SEASON],
        print_debug=False
    )

    assert written == ALL_ROWS
    assert len(team_games.get_all_team_game_data()) == ALL_ROWS

def test_the_seasons_a_source_covers_are_the_ones_it_has_and_no_others():
    source = FakeSource()

    assert source.seasons(date(2024, 12, 1), date(2025, 1, 1)) == [fake_data.SEASON_YEAR]
    assert source.seasons(date(1990, 1, 1), date(2025, 1, 1)) == [fake_data.SEASON_YEAR]

# THE SCHEDULE: #
def test_collecting_the_schedule_stores_games_that_have_not_been_played():
    upcoming = [
        fake_data.scheduled_game(game, status=GameStatus.SCHEDULED)
        for game in fake_data.SEASON_GAMES
    ]

    written = schedule.collect(
        FakeSource(schedule=upcoming),
        seasons=[fake_data.SEASON_YEAR],
        print_debug=False
    )

    stored = schedule_store.all_games()

    assert written == len(fake_data.SEASON_GAMES)
    assert len(stored) == len(fake_data.SEASON_GAMES)
    assert stored[0].game.date == fake_data.SEASON_GAMES[0].day
    assert stored[0].status is GameStatus.SCHEDULED

def test_recollecting_the_schedule_replaces_a_game_that_has_moved():
    """One request covers a whole season, so a postponed game is corrected rather than duplicated."""

    original = fake_data.SEASON_GAMES[0]
    postponed = PlayedGame(
        original.number,
        date(2024, 12, 20),
        original.home_team_id,
        original.away_team_id,
        0,
        0
    )

    schedule.collect(
        FakeSource(schedule=[fake_data.scheduled_game(original)]),
        seasons=[fake_data.SEASON_YEAR],
        print_debug=False
    )
    schedule.collect(
        FakeSource(schedule=[fake_data.scheduled_game(postponed)]),
        seasons=[fake_data.SEASON_YEAR],
        print_debug=False
    )

    stored = schedule_store.all_games()

    assert len(stored) == 1
    assert stored[0].game.date == postponed.day
