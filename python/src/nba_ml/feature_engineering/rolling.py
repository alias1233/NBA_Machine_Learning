import pandas as pd
from pandas.core.window.rolling import Rolling
from pandas.core.window.expanding import Expanding
from pandas.core.window.ewm import ExponentialMovingWindow
from typing import Callable
from dataclasses import dataclass

from nba_ml.feature_engineering import game_columns

@dataclass
class RollingCategory():
    """Defines a new column computed with a rolling function over another column."""

    column_name: str
    """Name of the new column."""

    calculated_from_column_name: str
    """Name of the column the rolling function is applied to."""

    rolling_function: Callable[[Rolling | Expanding | ExponentialMovingWindow], pd.Series]

    max_window_length: int | None = None
    """Window size in rows. None uses every earlier row."""

    halflife: float | None = None
    """If set, the window is exponentially weighted and max_window_length is ignored."""

    min_window_length: int = 1
    """Minimum number of rows needed in the window to produce a value."""

    exclusive: bool = True
    """If True, a row's own value is not included in its window."""

    fill_na_value: int | None = 0
    """Value used to fill NaN results. None leaves them as NaN."""

MEAN_FUNCTION: Callable[[Rolling | Expanding | ExponentialMovingWindow], pd.Series] = lambda x : x.mean()
STD_FUNCTION: Callable[[Rolling | Expanding | ExponentialMovingWindow], pd.Series] = lambda x : x.std()
COUNT_FUNCTION: Callable[[Rolling | Expanding | ExponentialMovingWindow], pd.Series] = lambda x : x.count()

def _grouping(dataframe: pd.DataFrame, group_by_column: str | list[str] | None):
    """Returns the group-by columns as a list of Series, or None if there is no grouping."""

    if group_by_column is None:
        return None

    if isinstance(group_by_column, str):
        return [dataframe[group_by_column]]

    return [dataframe[column] for column in group_by_column]

def calculate_rolling_function_column(
        dataframe: pd.DataFrame,
        rolling_param: RollingCategory,
        group_by_column: str | list[str] | None = None
        ) -> pd.Series:
    """The dataframe must be sorted within each group and have a unique index."""

    calculated_from_column = dataframe[rolling_param.calculated_from_column_name]
    groups = _grouping(dataframe, group_by_column)

    if rolling_param.exclusive:
        calculated_from_column = (
            calculated_from_column.shift(1) if groups is None
            else calculated_from_column.groupby(groups, sort=False).shift(1)
        )

    window = calculated_from_column if groups is None else calculated_from_column.groupby(groups, sort=False)

    if rolling_param.halflife is not None:
        window = window.ewm(
            halflife=rolling_param.halflife,
            min_periods=rolling_param.min_window_length
        )

    elif rolling_param.max_window_length is not None:
        window = window.rolling(
            window=rolling_param.max_window_length,
            min_periods=rolling_param.min_window_length
        )

    else:
        window = window.expanding(min_periods=rolling_param.min_window_length)

    rolling_column = rolling_param.rolling_function(window)

    if groups is not None:
        # Grouped results are indexed by group, so realign them with the dataframe's index.
        rolling_column = rolling_column.reset_index(
            level=list(range(len(groups))), drop=True
        ).reindex(dataframe.index)

    if rolling_param.fill_na_value is not None:
        rolling_column = rolling_column.fillna(rolling_param.fill_na_value)

    return rolling_column.astype(game_columns.BUILT_COLUMN_TYPE)

def add_rolling_function_columns(
        dataframe: pd.DataFrame,
        rolling_params: list[RollingCategory],
        group_by_column: str | list[str] | None = None
        ) -> pd.DataFrame:
    """Computes rolling functions on the given dataframe."""

    if not rolling_params:
        return dataframe

    new_columns = {
        rolling_param.column_name: calculate_rolling_function_column(dataframe, rolling_param, group_by_column)
        for rolling_param in rolling_params
    }

    return pd.concat([dataframe, pd.DataFrame(new_columns, index=dataframe.index)], axis=1)
