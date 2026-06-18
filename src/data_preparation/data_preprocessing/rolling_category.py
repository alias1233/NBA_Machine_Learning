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
        rolling_param: RollingCategory
        ) -> pd.Series:
    calculated_from_column = dataframe[rolling_param.calculated_from_column_name]

    if rolling_param.exclusive:
        calculated_from_column = calculated_from_column.shift(1)

    if rolling_param.max_window_length is not None:
        rolling_column = rolling_param.rolling_function(
        calculated_from_column.rolling(
            window=rolling_param.max_window_length, 
            min_periods=rolling_param.min_window_length
            ))
    
    else:
        rolling_column = rolling_param.rolling_function(
            calculated_from_column.expanding(
                min_periods=rolling_param.min_window_length
            )
        )
    
    if rolling_param.fill_na_value is not None:
        rolling_column = rolling_column.fillna(rolling_param.fill_na_value)

    return rolling_column

def add_rolling_function_columns(
        dataframe: pd.DataFrame, 
        rolling_params: list[RollingCategory]
        ) -> pd.DataFrame:
    """
    Computes rolling functions on the given dataframe. 
    """

    for rolling_param in rolling_params:
        dataframe[rolling_param.column_name] = calculate_rolling_function_column(dataframe, rolling_param)

    return dataframe