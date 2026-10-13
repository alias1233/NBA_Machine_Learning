"""Columns shared by player and team game rows, plus small helpers."""

import numpy as np
import pandas as pd
from typing import Any

BUILT_COLUMN_TYPE = np.float32
"""Data type used for every engineered column."""

def encode_equality_as_integer(column: pd.Series, value: Any) -> pd.Series:
    """Returns 1 where the column equals the value and 0 elsewhere."""

    return (column == value).astype(int)

def sort_columns_alphabetically(dataframe: pd.DataFrame) -> pd.DataFrame:
    return dataframe.sort_index(axis=1)

def column_or_grouped_column(
    dataframe: pd.DataFrame,
    column_name: str,
    group_by_column: str | list[str] | None
    ):
    """Returns the column, grouped by group_by_column if one is given."""

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
    """Adds a column for each pair with the first column minus the second."""

    for minuend_column, subtrahend_column in stat_columns:
        dataframe[minuend_column + DIFFERENCE_INFIX + subtrahend_column] = (
            dataframe[minuend_column] - dataframe[subtrahend_column]
        ).astype(BUILT_COLUMN_TYPE)
    return dataframe
