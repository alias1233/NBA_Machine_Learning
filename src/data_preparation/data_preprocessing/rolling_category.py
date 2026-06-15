import pandas as pd
from pandas.core.window.rolling import Rolling
from typing import Callable
from dataclasses import dataclass

@dataclass
class RollingCategory():
    column_name: str
    calculated_from_column_name: str
    window_length: int
    exclusive: bool
    rolling_function: Callable[[Rolling], pd.Series]

MEAN_FUNCTION: Callable[[Rolling], pd.Series] = lambda x : x.mean()
STD_FUNCTION: Callable[[Rolling], pd.Series] = lambda x : x.std()

def calculate_rolling_function_column(
        dataframe: pd.DataFrame, 
        rolling_param: RollingCategory
        ) -> pd.Series:
    calculated_from_column = dataframe[rolling_param.calculated_from_column_name]
    if rolling_param.exclusive:
        calculated_from_column = calculated_from_column.shift(1)
    return rolling_param.rolling_function(calculated_from_column.rolling(window=rolling_param.window_length))

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