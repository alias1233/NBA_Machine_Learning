"""
What any game row holds, whoever it is about, plus the two helpers every column builder uses.

The rest of the builders are grouped by what they describe: player_columns.py, team_columns.py,
schedule_columns.py and season_columns.py. Everything they share sits here, so nothing in that ring
imports another member of it.

Every builder takes column names rather than assuming them, so the same code builds a player frame
and a team frame. None of them decides which columns a model wants.
"""

import numpy as np
import pandas as pd
from typing import Any

BUILT_COLUMN_TYPE = np.float32
"""
What a column this package builds is kept as.

Every finished build is handed to a model as 32 bit floats, so a built column kept any wider is
memory spent on precision that is thrown away at the end, and these frames are the largest thing the
pipeline holds. Pandas works a rolling window out in 64 bits whatever it is given, so this is the
width a result is kept at rather than the width it is worked out at.

The columns read straight off a store keep the type they were stored as, because an id has to stay
exact and a box score count already costs nothing.
"""

def encode_equality_as_integer(column: pd.Series, value: Any) -> pd.Series:
    """One where the value matches, zero everywhere else."""

    return (column == value).astype(int)

def sort_columns_alphabetically(dataframe: pd.DataFrame) -> pd.DataFrame:
    return dataframe.sort_index(axis=1)

def column_or_grouped_column(
    dataframe: pd.DataFrame,
    column_name: str,
    group_by_column: str | list[str] | None
    ):
    """
    Returns the column, grouped when a group column is given, so diff and shift stay inside one
    group instead of reading whatever row happens to sit above.
    """

    if group_by_column is None:
        return dataframe[column_name]

    return dataframe.groupby(by=group_by_column, sort=False)[column_name]

POINTS = 'POINTS'
def add_points_column(
    game_data: pd.DataFrame,
    fgm_column: str,
    fg3m_column: str,
    ftm_column: str
    ) -> pd.DataFrame:
    fgm = game_data[fgm_column]
    fg3m = game_data[fg3m_column]
    ftm = game_data[ftm_column]
    game_data[POINTS] = (fgm - fg3m) * 2 + fg3m * 3 + ftm
    return game_data

REBOUNDS = 'REBOUNDS'
def add_total_rebounds_column(
    game_data: pd.DataFrame,
    orb_column: str,
    drb_column: str
    ) -> pd.DataFrame:
    orb = game_data[orb_column]
    drb = game_data[drb_column]
    game_data[REBOUNDS] = orb + drb
    return game_data

DIFFERENCE_INFIX = "_DIFF_FROM_"
def get_all_differences_columns(
    stat_columns: list[tuple[str, str]]
    ) -> list[str]:
    return [minuend_column + DIFFERENCE_INFIX + subtrahend_column for minuend_column, subtrahend_column in stat_columns]
def add_differences_columns(
    dataframe: pd.DataFrame,
    stat_columns: list[tuple[str, str]]
) -> pd.DataFrame:
    """Adds one column per pair, holding the first column minus the second."""

    for minuend_column, subtrahend_column in stat_columns:
        dataframe[minuend_column + DIFFERENCE_INFIX + subtrahend_column] = (
            dataframe[minuend_column] - dataframe[subtrahend_column]
        ).astype(BUILT_COLUMN_TYPE)
    return dataframe
