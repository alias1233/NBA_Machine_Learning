"""Schedule feature columns such as rest days and recent game counts."""

import numpy as np
import pandas as pd

from nba_ml.feature_engineering import season_columns
from nba_ml.feature_engineering.game_columns import BUILT_COLUMN_TYPE, column_or_grouped_column

REST = 'REST'
BREAK_LENGTH = 'BREAK_LENGTH'
SEASON_OPENER = 'SEASON_OPENER'
CAREER_DEBUT = 'CAREER_DEBUT'
MAX_REST = 7
MAX_BREAK_DAYS = 90
def add_break_columns(
    game_data: pd.DataFrame,
    game_date_column: str,
    max_rest: int = MAX_REST,
    max_break_days: int = MAX_BREAK_DAYS,
    group_by_column: str | None = None
    ) -> pd.DataFrame:
    """Adds the rest, break length, season opener and career debut columns. Rows must be sorted by date."""

    game_dates = game_data[game_date_column]
    groups = None if group_by_column is None else game_data[group_by_column]

    days_since_last_game = column_or_grouped_column(game_data, game_date_column, group_by_column).diff().dt.days - 1
    days_since_last_game = days_since_last_game.fillna(max_break_days).clip(lower=0, upper=max_break_days)

    season = season_columns.season_of(game_dates)
    previous_season = season.shift(1) if groups is None else season.groupby(groups, sort=False).shift(1)

    game_data[REST] = days_since_last_game.clip(upper=max_rest).astype(BUILT_COLUMN_TYPE)
    game_data[BREAK_LENGTH] = np.log1p(days_since_last_game).astype(BUILT_COLUMN_TYPE)
    # The previous season is only missing on a debut, which also counts as a season opener.
    game_data[SEASON_OPENER] = (season != previous_season).astype(int)
    game_data[CAREER_DEBUT] = previous_season.isna().astype(int)
    return game_data

GAMES_PLAYED = 'GAMES_PLAYED'
def add_games_played_column(
    game_data: pd.DataFrame,
    group_by_column: str
    ) -> pd.DataFrame:
    """Adds the number of earlier games in each row's group."""

    game_data[GAMES_PLAYED] = game_data.groupby(by=group_by_column, sort=False).cumcount()
    return game_data

RECENT_GAME_COUNT_PREFIX = 'GAMES_IN_LAST_'
RECENT_GAME_COUNT_DAYS = (7, 14)
def get_recent_game_count_columns(day_counts: tuple[int, ...] = RECENT_GAME_COUNT_DAYS) -> list[str]:
    return [f"{RECENT_GAME_COUNT_PREFIX}{days}_DAYS" for days in day_counts]
def add_recent_game_count_columns(
    game_data: pd.DataFrame,
    game_date_column: str,
    group_by_column: str,
    day_counts: tuple[int, ...] = RECENT_GAME_COUNT_DAYS
    ) -> pd.DataFrame:
    """Adds the number of games played in the last N days before each game."""

    COUNTED = "COUNTED"

    ordered = game_data[[group_by_column, game_date_column]].sort_values(
        by=[group_by_column, game_date_column]
    )
    ordered[COUNTED] = 1
    grouped = ordered.groupby(by=group_by_column, sort=False)

    columns = {}
    for days, column_name in zip(day_counts, get_recent_game_count_columns(day_counts)):
        within_days = grouped.rolling(f"{days}D", on=game_date_column)[COUNTED].count().to_numpy()
        columns[column_name] = pd.Series(
            within_days - 1, index=ordered.index, dtype=BUILT_COLUMN_TYPE
        ).reindex(game_data.index)

    return pd.concat([game_data, pd.DataFrame(columns, index=game_data.index)], axis=1)

TEAM_GAME_NUMBER = "TEAM_GAME_NUMBER"
def number_team_games(
    team_game_data: pd.DataFrame,
    game_id_column: str,
    team_id_column: str,
    game_date_column: str
    ) -> pd.DataFrame:
    """Returns each team's games numbered in date order, starting from 0."""

    team_games = team_game_data[[game_id_column, team_id_column, game_date_column]].sort_values(
        by=[team_id_column, game_date_column]
    )
    team_games[TEAM_GAME_NUMBER] = team_games.groupby(by=team_id_column, sort=False).cumcount()
    return team_games
