import pandas as pd
from pandas.core.window.rolling import Rolling
from pandas.core.window.expanding import Expanding
from pandas.core.window.ewm import ExponentialMovingWindow
from typing import Callable
from dataclasses import dataclass

@dataclass
class RollingCategory():
    """One new column, built by running a function over a window of another column."""

    column_name: str
    """What the new column is called."""

    calculated_from_column_name: str
    """The column the window reads."""

    rolling_function: Callable[[Rolling | Expanding | ExponentialMovingWindow], pd.Series]

    max_window_length: int | None = None
    """How many rows the window holds. None reads every earlier row."""

    halflife: float | None = None
    """
    If set, the window is exponentially weighted rather than flat, with a value this many rows back
    counting half as much as the newest one. max_window_length is then ignored. A flat window treats
    the row before last exactly like the oldest row still inside it, and a weighted one does not.
    """

    min_window_length: int = 1
    """How many rows the window needs before it produces a value rather than a blank."""

    exclusive: bool = True
    """
    Leaves a row's own value out of its window, so a column built this way only ever holds what was
    known before that row. This is what makes one feature build valid for a game not yet played.
    """

    fill_na_value: int | None = 0
    """What a blank becomes. None leaves it blank."""

MEAN_FUNCTION: Callable[[Rolling | Expanding | ExponentialMovingWindow], pd.Series] = lambda x : x.mean()
STD_FUNCTION: Callable[[Rolling | Expanding | ExponentialMovingWindow], pd.Series] = lambda x : x.std()
COUNT_FUNCTION: Callable[[Rolling | Expanding | ExponentialMovingWindow], pd.Series] = lambda x : x.count()

def _grouping(dataframe: pd.DataFrame, group_by_column: str | list[str] | None):
    """The columns to group by, as the list of series pandas wants, or None for one whole group."""

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
    """
    Args:
        group_by_column restarts the window for every group, so one call covers every group in the
        frame. Without it the whole column is treated as one group. Naming more than one column
        restarts the window per combination of them, which is what reading a subject's games of one
        kind takes.

    The frame must be sorted so that each group's rows are in the order the window should read them,
    and its row labels must be unique.
    """

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
        # A grouped window comes back keyed by group, so put the values back on the frame's own rows.
        rolling_column = rolling_column.reset_index(
            level=list(range(len(groups))), drop=True
        ).reindex(dataframe.index)

    if rolling_param.fill_na_value is not None:
        rolling_column = rolling_column.fillna(rolling_param.fill_na_value)

    return rolling_column

def add_rolling_function_columns(
        dataframe: pd.DataFrame,
        rolling_params: list[RollingCategory],
        group_by_column: str | list[str] | None = None
        ) -> pd.DataFrame:
    """
    Computes rolling functions on the given dataframe.

    The columns are attached in one step, because inserting them one at a time fragments the frame
    and gets slower as the frame widens. See calculate_rolling_function_column for group_by_column.
    """

    if not rolling_params:
        return dataframe

    new_columns = {
        rolling_param.column_name: calculate_rolling_function_column(dataframe, rolling_param, group_by_column)
        for rolling_param in rolling_params
    }

    return pd.concat([dataframe, pd.DataFrame(new_columns, index=dataframe.index)], axis=1)
