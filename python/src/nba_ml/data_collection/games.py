"""
Collecting finished box scores.

Player rows come from the data source. Team rows are totals of the player rows already stored.
"""

from datetime import date, timedelta
from typing import Iterable

import pandas as pd

from nba_ml import season
from nba_ml.season import SeasonType
from nba_ml.sources.base import DataSource
from nba_ml.stores import player_games, team_games

DEFAULT_UPDATE_LOOKBACK_DAYS = 1
"""Days before the newest stored game to refetch during an update."""

def _seasons_to_collect(
    source: DataSource,
    requested: Iterable[int] | None,
    date_from: date | None,
    date_to: date | None
    ) -> list[int]:
    """The requested source seasons that the project keeps."""

    available = source.seasons(date_from, date_to)
    requested = available if requested is None else requested
    return [
        season_year
        for season_year in requested
        if season_year >= season.COLLECTION_START_SEASON and season_year in available
    ]

def collect_player_games(
    source: DataSource,
    seasons: Iterable[int] | None = None,
    season_types: Iterable[SeasonType] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    print_debug: bool = True
    ) -> int:
    """
    Writes finished player box scores to the store and returns how many rows were written.

    Args:
        seasons defaults to every season the source covers that could hold a game in the dates given.
        season_types defaults to all of them.
        date_from and date_to keep the run to games played inside them, which is what a scheduled
        update asks for.
    """

    if date_to is not None and date_to < season.PLAYER_GAME_COLLECTION_START_DATE:
        return 0

    date_from = max(date_from or season.PLAYER_GAME_COLLECTION_START_DATE, season.PLAYER_GAME_COLLECTION_START_DATE)
    seasons = _seasons_to_collect(source, seasons, date_from, date_to)
    season_types = list(SeasonType) if season_types is None else list(season_types)
    rows_written = 0

    for season_year in seasons:
        for season_type in season_types:
            games = source.player_games(season_year, season_type, date_from, date_to)
            if games is None or games.empty:
                continue

            rows_written += player_games.store(games)
            if print_debug:
                print(f"player games: {season_year} {season_type.value.lower()}, {len(games)} rows")

    return rows_written

def collect_team_games(
    seasons: Iterable[int] | None = None,
    season_types: Iterable[SeasonType] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    print_debug: bool = True
    ) -> int:
    """Builds one team row per game from the player rows already stored."""

    players = (
        player_games.get_all_player_game_data()
        if date_from is None
        else player_games.get_game_data_after_date(date_from)
    )
    if players.empty:
        return 0

    game_dates = pd.to_datetime(players[player_games.GAME_DATE.category_name])
    if date_to is not None:
        players = players.loc[game_dates.dt.date <= date_to]
        game_dates = game_dates.loc[players.index]
    if seasons is not None:
        requested_seasons = set(seasons)
        season_years = game_dates.dt.year - (game_dates.dt.month < season.SEASON_START_MONTH)
        players = players.loc[season_years.isin(requested_seasons)]
    if season_types is not None:
        requested_types = {season.GAME_ID_PREFIXES[season_type] for season_type in season_types}
        players = players.loc[players[player_games.SEASON_TYPE.category_name].isin(requested_types)]
    if players.empty:
        return 0

    identifiers = [
        team_games.TEAM_ID.category_name,
        team_games.GAME_ID.category_name,
        team_games.GAME_DATE.category_name,
        team_games.SEASON_TYPE.category_name,
        team_games.MATCHUP.category_name,
        team_games.WIN_LOSS.category_name
    ]
    totalled = [
        team_games.MINUTES_PLAYED.category_name,
        team_games.FIELD_GOALS_MADE.category_name,
        team_games.FIELD_GOALS_ATTEMPTED.category_name,
        team_games.THREE_POINTERS_MADE.category_name,
        team_games.THREE_POINTERS_ATTEMPTED.category_name,
        team_games.FREE_THROWS_MADE.category_name,
        team_games.FREE_THROWS_ATTEMPTED.category_name,
        team_games.OFFENSIVE_REBOUNDS.category_name,
        team_games.DEFENSIVE_REBOUNDS.category_name,
        team_games.ASSISTS.category_name,
        team_games.STEALS.category_name,
        team_games.BLOCKS.category_name,
        team_games.TURNOVERS.category_name,
        team_games.PERSONAL_FOULS.category_name
    ]
    teams = players.groupby(identifiers, as_index=False, sort=False)[totalled].sum()
    written = team_games.store(teams)
    if print_debug:
        print(f"team games: {written} rows from stored player games")

    return written

def update_player_games(source: DataSource, print_debug: bool = True) -> int:
    """
    Collects every player box score played since the newest one already stored, which is what an
    hourly job runs. Collects everything when the store is empty.
    """

    return collect_player_games(source, date_from=player_games.latest_game_date(), print_debug=print_debug)

def update_team_games(print_debug: bool = True) -> int:
    """The same as update_player_games, for the team store."""

    return collect_team_games(date_from=team_games.latest_game_date(), print_debug=print_debug)

def collect_games(
    source: DataSource,
    seasons: Iterable[int] | None = None,
    season_types: Iterable[SeasonType] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    print_debug: bool = True
    ) -> int:
    """Fetches player rows, then builds team rows from the stored result."""

    seasons = None if seasons is None else tuple(seasons)
    season_types = None if season_types is None else tuple(season_types)
    player_count = collect_player_games(
        source, seasons, season_types, date_from, date_to, print_debug
    )
    team_count = collect_team_games(seasons, season_types, date_from, date_to, print_debug)
    return player_count + team_count

def update_start_date(
    latest_game_date: date | None,
    lookback_days: int = DEFAULT_UPDATE_LOOKBACK_DAYS
    ) -> date | None:
    """The first date one store needs for an incremental update."""

    if lookback_days < 0:
        raise ValueError("lookback_days cannot be negative.")

    return None if latest_game_date is None else latest_game_date - timedelta(days=lookback_days)

def update_games(
    source: DataSource,
    lookback_days: int = DEFAULT_UPDATE_LOOKBACK_DAYS,
    print_debug: bool = True
    ) -> int:
    """Updates each game store from its own newest row."""

    player_date_from = update_start_date(player_games.latest_game_date(), lookback_days)
    team_date_from = update_start_date(team_games.latest_game_date(), lookback_days)
    player_count = collect_player_games(source, date_from=player_date_from, print_debug=print_debug)
    team_count = collect_team_games(date_from=team_date_from, print_debug=print_debug)
    return player_count + team_count
