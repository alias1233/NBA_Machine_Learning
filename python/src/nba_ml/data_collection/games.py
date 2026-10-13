"""Collects box scores for finished games."""

from datetime import date, timedelta
from typing import Iterable

import pandas as pd

from nba_ml import season
from nba_ml.season import SeasonType
from nba_ml.sources.base import DataSource, SourceDataError
from nba_ml.stores import player_games, team_games

DEFAULT_UPDATE_LOOKBACK_DAYS = 1

AGREEING_ROWS = "AGREEING_ROWS"
"""Temporary column counting the player rows that share the same game labels."""


def require_resumable_player_archive():
    """Raises an error if the player game database exists but is empty."""

    if player_games.FILEPATH.exists() and player_games.latest_game_date() is None:
        raise RuntimeError(
            "The player-game database exists but has no rows. Refusing to start a full backfill over "
            "an emptied archive. Restore it, or use `nba-collect all --from-start` only to intentionally "
            "recollect it."
        )


def _validate_player_game_rows(rows: pd.DataFrame, season_year: int, season_type: SeasonType):
    phase = season_type.value.lower().replace("_", " ")
    if not isinstance(rows, pd.DataFrame):
        raise SourceDataError(f"{season_year} {phase} player games are not a table of rows.")

    required = player_games.DATABASE.category_names
    missing = [column for column in required if column not in rows]
    if missing:
        raise SourceDataError(
            f"{season_year} {phase} player games are missing required columns: {', '.join(missing)}."
        )

    malformed = rows[rows[required].isna().any(axis=1)]
    if not malformed.empty:
        identifiers = [player_games.PLAYER_ID.category_name, player_games.GAME_ID.category_name]
        found = ", ".join(
            f"player {row[identifiers[0]]}, game {row[identifiers[1]]}"
            for _, row in malformed[identifiers].head(5).iterrows()
        )
        raise SourceDataError(
            f"{season_year} {phase} player games contain {len(malformed)} malformed row(s): {found}."
        )

    identifiers = [player_games.PLAYER_ID.category_name, player_games.GAME_ID.category_name]
    duplicated = rows.duplicated(identifiers, keep=False)
    if duplicated.any():
        raise SourceDataError(
            f"{season_year} {phase} player games repeat {int(duplicated.sum())} player-game row(s)."
        )


def _seasons_to_collect(
    source: DataSource,
    requested: Iterable[int] | None,
    date_from: date | None,
    date_to: date | None
    ) -> list[int]:
    """Returns the requested seasons that the source has and the project collects."""

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
    """Fetches finished player box scores, stores them, and returns the number of rows written."""

    if date_to is not None and date_to < season.PLAYER_GAME_COLLECTION_START_DATE:
        return 0

    date_from = max(date_from or season.PLAYER_GAME_COLLECTION_START_DATE, season.PLAYER_GAME_COLLECTION_START_DATE)
    seasons = _seasons_to_collect(source, seasons, date_from, date_to)
    season_types = list(SeasonType) if season_types is None else list(season_types)
    rows_written = 0

    for season_year in seasons:
        for season_type in season_types:
            for batch in source.player_game_batches(season_year, season_type, date_from, date_to):
                if batch is None:
                    phase = season_type.value.lower().replace("_", " ")
                    raise SourceDataError(
                        f"{season_year} {phase} player games could not be fetched."
                    )
                if batch.empty:
                    continue
                _validate_player_game_rows(batch, season_year, season_type)

                stored = player_games.store(batch)
                rows_written += stored
                if print_debug:
                    phase = season_type.value.lower().replace("_", " ")
                    print(f"player games: {season_year} {phase}, stored {stored} rows")

    return rows_written

def collect_team_games(
    seasons: Iterable[int] | None = None,
    season_types: Iterable[SeasonType] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    print_debug: bool = True
    ) -> int:
    """Builds team game rows by summing the stored player rows. Returns the number of rows written."""

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
        team_games.GAME_ID.category_name
    ]
    labels = [
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
    # Some old games have inconsistent labels within a team, so use the most common one.
    described = (
        players.groupby(identifiers + labels, sort=False, dropna=False).size()
        .reset_index(name=AGREEING_ROWS)
        .sort_values(AGREEING_ROWS, ascending=False, kind="stable")
        .drop_duplicates(identifiers)
        .drop(columns=AGREEING_ROWS)
    )
    totals = players.groupby(identifiers, as_index=False, sort=False)[totalled].sum()
    written = team_games.store(totals.merge(described, on=identifiers))
    if print_debug:
        print(f"team games: {written} rows from stored player games")

    return written

def update_player_games(source: DataSource, print_debug: bool = True) -> int:
    """Collects player box scores from the latest stored game date onwards."""

    return collect_player_games(source, date_from=player_games.latest_game_date(), print_debug=print_debug)

def update_team_games(print_debug: bool = True) -> int:
    return collect_team_games(date_from=team_rebuild_start_date(), print_debug=print_debug)

def collect_games(
    source: DataSource,
    seasons: Iterable[int] | None = None,
    season_types: Iterable[SeasonType] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    print_debug: bool = True
    ) -> int:
    """Collects player rows, then builds the team rows from them."""

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
    if lookback_days < 0:
        raise ValueError("lookback_days cannot be negative.")

    return None if latest_game_date is None else latest_game_date - timedelta(days=lookback_days)

def team_rebuild_start_date(lookback_days: int = 0) -> date | None:
    """Returns the date to rebuild team rows from so that every stored game gets one."""

    starts = [
        start for start in (
            player_games.oldest_game_date_outside(team_games.stored_game_ids()),
            update_start_date(team_games.latest_game_date(), lookback_days)
        )
        if start is not None
    ]

    return min(starts) if starts else None

def update_games(
    source: DataSource,
    lookback_days: int = DEFAULT_UPDATE_LOOKBACK_DAYS,
    print_debug: bool = True
    ) -> int:
    """Collects new player rows, then rebuilds any missing team rows."""

    player_date_from = update_start_date(player_games.latest_game_date(), lookback_days)
    player_count = collect_player_games(source, date_from=player_date_from, print_debug=print_debug)

    # Computed after the player rows are stored so the new games are included.
    team_count = collect_team_games(date_from=team_rebuild_start_date(lookback_days), print_debug=print_debug)
    return player_count + team_count
