"""
Collecting data into the stores, with a stand in service in place of the real one.

Nothing here reaches the network. The point is the part between the service and the store: which
seasons and dates get asked for, what lands in a table, what an update run does the second time it
is run, and what happens when the service refuses to answer. See tests/fake_data.py for the source.
"""

import sys
from datetime import date, timedelta

import pandas as pd
import pytest

from nba_ml import season
from nba_ml.cli import collect as collect_command
from nba_ml.data_collection import games, players, schedule, teams
from nba_ml.entities import GameStatus
from nba_ml.season import SeasonType
from nba_ml.sources.base import PLAYER_GAME_BATCH_SIZE, SourceAuthenticationError, SourceDataError
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

def test_recent_player_update_does_not_fetch_the_full_player_directory():
    known = fake_data.ALL_PLAYERS[:-1]
    players.collect(FakeSource(known_players=known), print_debug=False)
    player_games.store(fake_data.player_game_frame())

    source = FakeSource()
    written = players.update_from_games(source, date(2024, 10, 30), print_debug=False)

    assert written == 1
    assert "players" not in source.requests
    assert sum(request.startswith("player_info") for request in source.requests) == 1

def test_a_player_whose_information_did_not_arrive_is_asked_for_again(monkeypatch):
    """
    A player with no information row has every one of their games dropped from the feature build,
    so a failed request has to be retried rather than waiting on the day they next play.
    """

    missed = fake_data.ALL_PLAYERS[-1]
    rows = fake_data.player_game_frame()
    # They stopped playing well before the hourly run's own lookback, which is what makes a window
    # that narrow never ask about them again.
    sat_out = (rows[player_games.GAME_DATE.category_name] >= "2024-11-02") & (
        rows[player_games.PLAYER_ID.category_name] == missed.id
    )
    player_games.store(rows[~sat_out])
    players.collect(FakeSource(known_players=fake_data.ALL_PLAYERS[:-1]), print_debug=False)

    assert missed.id not in player_games.player_ids_since(
        games.update_start_date(player_games.latest_game_date())
    )

    source = FakeSource()
    monkeypatch.setattr(collect_command.teams, "collect", lambda *_: 0)
    monkeypatch.setattr(collect_command.games, "update_games", lambda *_: 0)

    collect_command.collect_all(source, refresh_schedule=False, print_debug=False)

    assert f"player_info {missed.id}" in source.requests
    assert players_store.get_player(missed.id) == missed


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

    assert games.collect_games(source, print_debug=False) == ALL_ROWS * (1 + fake_data.PLAYERS_PER_TEAM)

    stored = team_games.get_all_team_game_data()

    assert len(stored) == ALL_ROWS
    assert team_games.latest_game_date() == fake_data.SEASON_GAMES[-1].day
    assert player_games.latest_game_date() == fake_data.SEASON_GAMES[-1].day
    assert team_games.stored_game_ids() == {game.id for game in fake_data.SEASON_GAMES}

def test_a_date_narrows_a_collection_run_to_the_games_inside_it():
    player_games.store(fake_data.player_game_frame())
    from_date = date(2024, 10, 30)

    written = games.collect_team_games(date_from=from_date, print_debug=False)

    stored = team_games.get_all_team_game_data()
    days = {row for row in stored[team_games.GAME_DATE.category_name]}

    assert written == len(stored)
    assert min(days) == "2024-10-30"

def test_collection_does_not_request_seasons_before_the_project_floor():
    source = FakeSource()
    source.oldest_season = 1946

    written = games.collect_player_games(
        source,
        seasons=[1984, fake_data.SEASON_YEAR],
        season_types=[SeasonType.REGULAR_SEASON],
        print_debug=False
    )

    assert written == ALL_ROWS * fake_data.PLAYERS_PER_TEAM
    assert all(f" {fake_data.SEASON_YEAR} " in request for request in source.requests)

def test_player_collection_does_not_request_a_date_range_before_its_floor():
    source = FakeSource()
    source.oldest_season = 1946

    written = games.collect_player_games(
        source,
        date_from=date(1985, 10, 1),
        date_to=season.PLAYER_GAME_COLLECTION_START_DATE - timedelta(days=1),
        print_debug=False
    )

    assert written == 0
    assert source.requests == []

def test_player_collection_starts_the_first_legal_season_on_its_exact_floor():
    assert season.PLAYER_GAME_COLLECTION_START_DATE == date(2019, 10, 22)

    source = FakeSource()
    source.oldest_season = 1946

    games.collect_player_games(
        source,
        seasons=[season.COLLECTION_START_SEASON],
        season_types=[SeasonType.REGULAR_SEASON],
        print_debug=False
    )

    assert source.requests == [
        f"player_games {season.COLLECTION_START_SEASON} REGULAR_SEASON "
        f"{season.PLAYER_GAME_COLLECTION_START_DATE} None"
    ]

def test_team_games_are_built_from_stored_player_rows_without_a_source_request():
    stored_players = fake_data.player_game_frame()
    player_games.store(stored_players)

    written = games.collect_team_games(print_debug=False)

    stored_teams = team_games.get_all_team_game_data()
    first = stored_teams.iloc[0]
    same_team_game = stored_players.loc[
        (stored_players[player_games.TEAM_ID.category_name] == first[team_games.TEAM_ID.category_name])
        & (stored_players[player_games.GAME_ID.category_name] == first[team_games.GAME_ID.category_name])
    ]
    assert written == ALL_ROWS
    assert first[team_games.FIELD_GOALS_MADE.category_name] == same_team_game[
        player_games.FIELD_GOALS_MADE.category_name
    ].sum()

def test_a_team_row_holds_its_whole_box_score_when_its_players_are_labelled_inconsistently():
    """
    Measured in the nba.com archive on 2026-08-15: 37 team games label one team's own players two
    different ways. Summing over the label as well as the key would split that team's box score in
    two and store whichever half was written last, silently short.
    """

    rows = fake_data.player_game_frame()
    first_team_game = (
        (rows[player_games.GAME_ID.category_name] == fake_data.SEASON_GAMES[0].id)
        & (rows[player_games.TEAM_ID.category_name] == fake_data.SEASON_GAMES[0].home_team_id)
    )
    disagreeing = rows[first_team_game].index[0]
    rows.loc[disagreeing, player_games.MATCHUP.category_name] = "ANC vs. XXX"
    player_games.store(rows)

    games.collect_team_games(print_debug=False)

    stored = team_games.get_all_team_game_data()
    summed = stored[
        (stored[team_games.GAME_ID.category_name] == fake_data.SEASON_GAMES[0].id)
        & (stored[team_games.TEAM_ID.category_name] == fake_data.SEASON_GAMES[0].home_team_id)
    ]

    assert len(stored) == ALL_ROWS
    assert len(summed) == 1
    assert summed[team_games.FIELD_GOALS_MADE.category_name].item() == rows.loc[
        first_team_game, player_games.FIELD_GOALS_MADE.category_name
    ].sum()
    assert summed[team_games.MATCHUP.category_name].item() == "ANC vs. BRK"


def test_team_rows_are_built_from_player_rows_that_name_no_season_phase():
    """An archive collected before the phase was stored explicitly leaves the column empty."""

    rows = fake_data.player_game_frame()
    rows[player_games.SEASON_TYPE.category_name] = None
    player_games.store(rows)

    written = games.collect_team_games(print_debug=False)

    assert written == ALL_ROWS
    assert team_games.get_all_team_game_data()[team_games.SEASON_TYPE.category_name].isna().all()


def test_team_game_command_does_not_create_a_data_source(monkeypatch):
    def fail_if_called(*_):
        raise AssertionError("A source was created.")

    player_games.store(fake_data.player_game_frame())
    monkeypatch.setattr(collect_command.sources, "get_source", fail_if_called)
    monkeypatch.setattr(collect_command.source_identity, "claim", lambda _: None)
    monkeypatch.setattr(sys, "argv", ["nba-collect", "--quiet", "team-games", "--all-seasons"])

    collect_command.main()

    assert len(team_games.get_all_team_game_data()) == ALL_ROWS

def test_an_update_run_uses_each_store_own_lookback_date():
    """
    This is what an hourly job runs, and it is the whole reason a run is cheap.

    The previous day is included so a late-finalized game and every game on the latest stored date
    are rewritten rather than missed.
    """

    player_games.store(fake_data.player_game_frame())
    team_games.store(fake_data.team_game_frame(fake_data.SEASON_GAMES[:4]))

    updating = FakeSource()
    written = games.update_games(updating, print_debug=False)

    assert any(
        request.startswith("player_games") and str(date(2024, 11, 4)) in request
        for request in updating.requests
    )
    assert all(not request.startswith("team_games") for request in updating.requests)
    assert written == 4 * fake_data.PLAYERS_PER_TEAM + 18
    assert len(team_games.get_all_team_game_data()) == ALL_ROWS

def test_games_backfilled_behind_the_team_store_still_get_team_rows():
    """
    A team row is a total of player rows, so the team store can only follow the player one while
    games arrive newest first. A backfill writes games older than anything the team store holds, and
    a rebuild starting at its own newest row would step straight over them. Those games would then
    sit in the archive and reach no model, because a player row whose game has no team row is
    dropped where the two frames meet.
    """

    newest = fake_data.SEASON_GAMES[-2:]
    player_games.store(fake_data.player_game_frame(newest))
    team_games.store(fake_data.team_game_frame(newest))

    player_games.store(fake_data.player_game_frame(fake_data.SEASON_GAMES[:-2]))
    games.update_team_games(print_debug=False)

    assert team_games.stored_game_ids() == {game.id for game in fake_data.SEASON_GAMES}

def test_an_empty_team_store_rebuilds_from_all_stored_player_games():
    player_games.store(fake_data.player_game_frame())
    source = FakeSource()

    games.update_games(source, print_debug=False)

    assert any(
        request.startswith("player_games") and str(date(2024, 11, 4)) in request
        for request in source.requests
    )
    assert len(team_games.get_all_team_game_data()) == ALL_ROWS

def test_all_command_keeps_player_collection_at_its_own_lookback(monkeypatch):
    player_games.store(fake_data.player_game_frame())
    source = FakeSource()

    monkeypatch.setattr(collect_command.sources, "get_source", lambda *_: source)
    monkeypatch.setattr(collect_command.source_identity, "claim", lambda _: None)
    monkeypatch.setattr(collect_command.teams, "collect", lambda *_: 0)
    monkeypatch.setattr(collect_command.players, "update_from_games", lambda *_: 0)
    monkeypatch.setattr(collect_command.schedule, "collect", lambda *_, **__: 0)
    monkeypatch.setattr(sys, "argv", ["nba-collect", "--quiet", "all", "--lookback-days", "2"])

    collect_command.main()

    assert any(
        request.startswith("player_games") and str(date(2024, 11, 3)) in request
        for request in source.requests
    )
    assert len(team_games.get_all_team_game_data()) == ALL_ROWS


def test_all_command_from_start_rescans_without_clearing_existing_rows(monkeypatch):
    player_games.store(fake_data.player_game_frame())
    source = FakeSource()

    monkeypatch.setattr(collect_command.sources, "get_source", lambda *_: source)
    monkeypatch.setattr(collect_command.source_identity, "claim", lambda _: None)
    monkeypatch.setattr(collect_command.teams, "collect", lambda *_: 0)
    monkeypatch.setattr(collect_command.players, "update", lambda *_: 0)
    monkeypatch.setattr(collect_command.schedule, "collect", lambda *_, **__: 0)
    monkeypatch.setattr(sys, "argv", ["nba-collect", "--quiet", "all", "--from-start"])

    collect_command.main()

    assert any(
        str(season.PLAYER_GAME_COLLECTION_START_DATE) in request
        for request in source.requests
        if request.startswith("player_games")
    )
    assert len(player_games.get_all_player_game_data()) == ALL_ROWS * fake_data.PLAYERS_PER_TEAM


def test_all_command_refuses_an_existing_empty_player_archive(monkeypatch):
    with player_games.DATABASE:
        pass

    monkeypatch.setattr(
        collect_command.sources,
        "get_source",
        lambda *_: (_ for _ in ()).throw(AssertionError("A source was created."))
    )
    monkeypatch.setattr(collect_command.source_identity, "claim", lambda _: None)
    monkeypatch.setattr(sys, "argv", ["nba-collect", "--quiet", "all"])

    with pytest.raises(RuntimeError, match="--from-start"):
        collect_command.main()

def test_collecting_the_same_games_twice_rewrites_them_rather_than_duplicating_them():
    player_games.store(fake_data.player_game_frame())

    games.collect_team_games(print_debug=False)
    games.collect_team_games(print_debug=False)

    assert len(team_games.get_all_team_game_data()) == ALL_ROWS

def test_a_season_the_service_refuses_is_skipped_and_the_rest_of_the_run_carries_on():
    """A long run must not be lost to one season the service will not answer for."""

    source = FakeSource(failing_seasons=[fake_data.SEASON_YEAR - 1])

    written = games.collect_player_games(
        source,
        seasons=[fake_data.SEASON_YEAR - 1, fake_data.SEASON_YEAR],
        season_types=[SeasonType.REGULAR_SEASON],
        print_debug=False
    )

    assert written == ALL_ROWS * fake_data.PLAYERS_PER_TEAM
    assert len(player_games.get_all_player_game_data()) == ALL_ROWS * fake_data.PLAYERS_PER_TEAM


def test_player_collection_does_not_claim_storage_when_the_store_fails(monkeypatch, capsys):
    source = FakeSource()

    def fail_store(_):
        raise RuntimeError("disk write failed")

    monkeypatch.setattr(player_games, "store", fail_store)

    with pytest.raises(RuntimeError, match="disk write failed"):
        games.collect_player_games(source)

    assert "stored" not in capsys.readouterr().out


def test_player_collection_keeps_stored_batches_when_a_later_batch_fails():
    rows = fake_data.player_game_frame()
    rows_per_game = fake_data.PLAYERS_PER_TEAM * 2
    first_batch = rows.iloc[:rows_per_game * 2]
    second_batch = rows.iloc[rows_per_game * 2:rows_per_game * 4]

    class InterruptedSource(FakeSource):
        def player_game_batches(self, *_):
            yield first_batch
            yield second_batch
            raise RuntimeError("connection lost")

    with pytest.raises(RuntimeError, match="connection lost"):
        games.collect_player_games(
            InterruptedSource(),
            seasons=[fake_data.SEASON_YEAR],
            season_types=[SeasonType.REGULAR_SEASON],
            print_debug=False
        )

    stored = player_games.get_all_player_game_data()
    assert len(stored) == len(first_batch) + len(second_batch)
    assert set(stored[player_games.GAME_ID.category_name]) == {
        fake_data.SEASON_GAMES[0].id,
        fake_data.SEASON_GAMES[1].id,
        fake_data.SEASON_GAMES[2].id,
        fake_data.SEASON_GAMES[3].id
    }


def test_legacy_player_game_source_batches_whole_games_at_the_shared_limit():
    game_id = PLAYER_GAME_BATCH_SIZE - 1
    rows = pd.DataFrame({
        player_games.GAME_ID.category_name: [*range(game_id), game_id, game_id]
    })

    class LegacySource(FakeSource):
        def player_games(self, *_):
            return rows

    batches = list(LegacySource().player_game_batches(fake_data.SEASON_YEAR, SeasonType.REGULAR_SEASON))

    assert all(len(batch) <= PLAYER_GAME_BATCH_SIZE for batch in batches)
    assert pd.concat(batches, ignore_index=True).equals(rows)
    assert [len(batch) for batch in batches] == [PLAYER_GAME_BATCH_SIZE - 1, 2]
    matching = [
        batch for batch in batches if (batch[player_games.GAME_ID.category_name] == game_id).any()
    ]
    assert len(matching) == 1
    assert (matching[0][player_games.GAME_ID.category_name] == game_id).sum() == 2


def test_an_authentication_failure_keeps_completed_player_games_and_their_resume_date():
    player_games.store(fake_data.player_game_frame())
    requested_dates = []

    class RejectedSource(FakeSource):
        def player_games(self, season_year, season_type, date_from=None, date_to=None):
            requested_dates.append(date_from)
            raise SourceAuthenticationError("access ended")

    with pytest.raises(SourceAuthenticationError, match="access ended"):
        games.update_games(RejectedSource(), print_debug=False)

    assert len(player_games.get_all_player_game_data()) == ALL_ROWS * fake_data.PLAYERS_PER_TEAM
    assert player_games.latest_game_date() == fake_data.SEASON_GAMES[-1].day
    assert requested_dates == [fake_data.SEASON_GAMES[-1].day - timedelta(days=1)]


def test_an_exhausted_fetch_stops_the_run_without_advancing_the_resume_date():
    player_games.store(fake_data.player_game_frame())

    class UnavailableSource(FakeSource):
        def player_games(self, *_):
            return None

    with pytest.raises(SourceDataError, match="could not be fetched"):
        games.update_games(UnavailableSource(), print_debug=False)

    assert player_games.latest_game_date() == fake_data.SEASON_GAMES[-1].day


def test_a_malformed_source_row_stops_before_any_of_its_batch_is_stored():
    rows = fake_data.player_game_frame().iloc[:2].copy()
    rows.loc[rows.index[0], player_games.PLUS_MINUS.category_name] = None

    class MalformedSource(FakeSource):
        def player_games(self, *_):
            return rows

    with pytest.raises(SourceDataError, match="player .* game"):
        games.collect_player_games(MalformedSource(), print_debug=False)

    assert player_games.get_all_player_game_data().empty

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


def test_a_failed_schedule_fetch_stops_the_update():
    class UnavailableSource(FakeSource):
        def schedule(self, _):
            return None

    with pytest.raises(SourceDataError, match="schedule could not be fetched"):
        schedule.collect(UnavailableSource(), seasons=[fake_data.SEASON_YEAR], print_debug=False)
