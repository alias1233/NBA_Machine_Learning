"""
Where a game sits in the run of games before it: the gap, the pile up, and its number in the order.

Everything here is known the moment a game is scheduled, so a game not yet played gets the same
columns a played one does. None of it reads what happened in the game itself.

Every builder takes column names rather than assuming them, so the same code builds a player frame
and a team frame.
"""

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
    """
    Adds the four columns describing the gap before each game.

    REST is days off capped at max_rest, the range almost every game falls in. BREAK_LENGTH covers
    the whole range as the logarithm of one plus the days off. SEASON_OPENER and CAREER_DEBUT mark
    the two gaps that are not layoffs at all, and a career debut is given the longest gap.

    The given game_data must be sorted by game date, grouped by id, and the game_date column must be
    in datetime form.

    Args:
        group_by_column covers every group in one pass. Without it the frame must hold one group.
    """

    game_dates = game_data[game_date_column]
    groups = None if group_by_column is None else game_data[group_by_column]

    days_since_last_game = column_or_grouped_column(game_data, game_date_column, group_by_column).diff().dt.days - 1
    days_since_last_game = days_since_last_game.fillna(max_break_days).clip(lower=0, upper=max_break_days)

    season = season_columns.season_of(game_dates)
    previous_season = season.shift(1) if groups is None else season.groupby(groups, sort=False).shift(1)

    game_data[REST] = days_since_last_game.clip(upper=max_rest).astype(BUILT_COLUMN_TYPE)
    game_data[BREAK_LENGTH] = np.log1p(days_since_last_game).astype(BUILT_COLUMN_TYPE)
    # A missing previous season only happens on a debut, which counts as opening a season too.
    game_data[SEASON_OPENER] = (season != previous_season).astype(int)
    game_data[CAREER_DEBUT] = previous_season.isna().astype(int)
    return game_data

GAMES_PLAYED = 'GAMES_PLAYED'
def add_games_played_column(
    game_data: pd.DataFrame,
    group_by_column: str
    ) -> pd.DataFrame:
    """
    Counts how many games came before each row, within each group. Rolling columns fill their first
    rows with a set value, so this is what tells a model whether to trust the averages beside it.

    The given game_data must be sorted so that each group runs from oldest to newest.
    """

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
    """
    Adds how many games came before each one within the given number of days, not counting itself.
    Rest only measures the last gap, so three games in five nights reads the same as one without it.

    The frame need not be sorted, but its row labels must be unique and the date column must be in
    datetime form.
    """

    COUNTED = "COUNTED"

    # Sorted here rather than demanded of the caller, because a time based window has to read a
    # group in date order and the grouped result comes back in whatever order the groups were met.
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
    """
    Returns each team's games numbered from its first, so that "the game before this one" becomes a
    subtraction and the comparisons built on it become joins.

    The date column must be in datetime form. The frame need not be sorted.
    """

    team_games = team_game_data[[game_id_column, team_id_column, game_date_column]].sort_values(
        by=[team_id_column, game_date_column]
    )
    team_games[TEAM_GAME_NUMBER] = team_games.groupby(by=team_id_column, sort=False).cumcount()
    return team_games
