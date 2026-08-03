import pandas as pd
from pandas.core.window.rolling import Rolling
from pandas.core.window.expanding import Expanding
from typing import Callable
from dataclasses import dataclass

@dataclass
class RollingCategory():
    """
    Defines a rolling category which calculates rolling functions on another column.
    """

    column_name: str
    """
    Name of the rolling category column
    """

    calculated_from_column_name: str
    """
    Name of the targeted column to calculate rolling functions on
    """

    rolling_function: Callable[[Rolling | Expanding], pd.Series]
    """
    Function to apply to calculate the new column
    """

    max_window_length: int | None = None
    """
    Max window length of the rolling calculations. 
    If None, then the rolling function will calculate based on every value in the entire column.
    """

    min_window_length: int = 1
    """
    Minimum window length of the rolling calculations.. 
    """

    exclusive: bool = True
    """
    If True, the value at an index of the rolling column will exclude the corresponding value at the same index from the calcualted_from_column   
    """

    fill_na_value: int | None = 0
    """
    The value to fill NAN values with in the rolling column after calculations.
    If None, then the NAN values will be left as NAN in the rolling column.
    """

MEAN_FUNCTION: Callable[[Rolling | Expanding], pd.Series] = lambda x : x.mean()
STD_FUNCTION: Callable[[Rolling | Expanding], pd.Series] = lambda x : x.std()

def calculate_rolling_function_column(
        dataframe: pd.DataFrame,
        rolling_param: RollingCategory,
        group_by_column: str | None = None
        ) -> pd.Series:
    """
    Args:
        group_by_column restarts the window for every group, so one call covers every group in the
        frame. Without it the whole column is treated as one group.

    The frame must be sorted so that each group's rows are in the order the window should read them,
    and its row labels must be unique.
    """

    calculated_from_column = dataframe[rolling_param.calculated_from_column_name]
    groups = None if group_by_column is None else dataframe[group_by_column]

    if rolling_param.exclusive:
        calculated_from_column = (
            calculated_from_column.shift(1) if groups is None
            else calculated_from_column.groupby(groups, sort=False).shift(1)
        )

    window = calculated_from_column if groups is None else calculated_from_column.groupby(groups, sort=False)

    if rolling_param.max_window_length is not None:
        rolling_column = rolling_param.rolling_function(
            window.rolling(
                window=rolling_param.max_window_length,
                min_periods=rolling_param.min_window_length
                ))

    else:
        rolling_column = rolling_param.rolling_function(
            window.expanding(
                min_periods=rolling_param.min_window_length
            )
        )

    if groups is not None:
        # A grouped window comes back keyed by group, so put the values back on the frame's own rows.
        rolling_column = rolling_column.reset_index(level=0, drop=True).reindex(dataframe.index)

    if rolling_param.fill_na_value is not None:
        rolling_column = rolling_column.fillna(rolling_param.fill_na_value)

    return rolling_column

def add_rolling_function_columns(
        dataframe: pd.DataFrame,
        rolling_params: list[RollingCategory],
        group_by_column: str | None = None
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
