"""
Collecting finished box scores.

The player and team stores are the same fetch seen two ways, one row per player and one row per
team, so they share the loop over seasons.
"""

from datetime import date
from typing import Callable, Iterable

import pandas as pd

from nba_ml import season
from nba_ml.season import SeasonType
from nba_ml.sources.base import DataSource
from nba_ml.stores import player_games, team_games

GameLogFetch = Callable[[int, SeasonType, date | None, date | None], pd.DataFrame | None]
"""Asks a source for one season phase of box scores. Either DataSource.player_games or .team_games."""

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

def _collect(
    source: DataSource,
    fetch: GameLogFetch,
    store: Callable[[pd.DataFrame], int],
    label: str,
    seasons: Iterable[int] | None,
    season_types: Iterable[SeasonType] | None,
    date_from: date | None,
    date_to: date | None,
    print_debug: bool
    ) -> int:
    seasons = _seasons_to_collect(source, seasons, date_from, date_to)
    season_types = list(SeasonType) if season_types is None else list(season_types)

    rows_written = 0
    for season_year in seasons:
        for season_type in season_types:
            games = fetch(season_year, season_type, date_from, date_to)
            if games is None or games.empty:
                continue

            rows_written += store(games)

            if print_debug:
                print(f"{label}: {season_year} {season_type.value.lower()}, {len(games)} rows")

    return rows_written

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

    return _collect(
        source,
        source.player_games,
        player_games.store,
        "player games",
        seasons,
        season_types,
        date_from,
        date_to,
        print_debug
    )

def collect_team_games(
    source: DataSource,
    seasons: Iterable[int] | None = None,
    season_types: Iterable[SeasonType] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    print_debug: bool = True
    ) -> int:
    """The same as collect_player_games, one row per team per game instead of per player."""

    return _collect(
        source,
        source.team_games,
        team_games.store,
        "team games",
        seasons,
        season_types,
        date_from,
        date_to,
        print_debug
    )

def update_player_games(source: DataSource, print_debug: bool = True) -> int:
    """
    Collects every player box score played since the newest one already stored, which is what an
    hourly job runs. Collects everything when the store is empty.
    """

    return collect_player_games(source, date_from=player_games.latest_game_date(), print_debug=print_debug)

def update_team_games(source: DataSource, print_debug: bool = True) -> int:
    """The same as update_player_games, for the team store."""

    return collect_team_games(source, date_from=team_games.latest_game_date(), print_debug=print_debug)

def collect_games(
    source: DataSource,
    seasons: Iterable[int] | None = None,
    season_types: Iterable[SeasonType] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    print_debug: bool = True
    ) -> int:
    """Collects both stores together, allowing a source to share one response."""

    seasons = _seasons_to_collect(source, seasons, date_from, date_to)
    season_types = list(SeasonType) if season_types is None else list(season_types)
    rows_written = 0

    for season_year in seasons:
        for season_type in season_types:
            players, teams = source.game_rows(season_year, season_type, date_from, date_to)
            player_count = 0 if players is None or players.empty else player_games.store(players)
            team_count = 0 if teams is None or teams.empty else team_games.store(teams)
            rows_written += player_count + team_count

            if print_debug and (player_count or team_count):
                print(
                    f"games: {season_year} {season_type.value.lower()}, "
                    f"{player_count} player rows, {team_count} team rows"
                )

    return rows_written

def update_games(source: DataSource, print_debug: bool = True) -> int:
    """Updates both game stores from the oldest point either one still needs."""

    newest_player = player_games.latest_game_date()
    newest_team = team_games.latest_game_date()
    date_from = None if newest_player is None or newest_team is None else min(newest_player, newest_team)
    return collect_games(source, date_from=date_from, print_debug=print_debug)
