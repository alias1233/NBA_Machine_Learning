import pandas as pd
from pandas.core.window.rolling import Rolling
from typing import Any, Callable
from dataclasses import dataclass

POINTS = 'POINTS'
REBOUNDS = 'REBOUNDS'

# Represents the number of days without a game inbetween the current game and the player's last played game.
REST = 'REST'

POSSESSIONS = 'POSSESSIONS'

# A value of 0 represents home, and a value of 1 represents away.
HOME_OR_AWAY = 'HOME_OR_AWAY'

### SEASON TYPES: A value of 1 represents True, and a value of 0 represents False. ###
PRESEASON = 'PRESEASON'
REGULAR_SEASON = 'REGULAR_SEASON'
PLAYOFFS = 'PLAYOFFS'
PLAY_IN = 'PLAY_IN'

def sort_by_date(
        dataframe: pd.DataFrame, 
        data_column_name: str, 
        date_format: str | None = None
        ) -> pd.DataFrame:
    """
    Converts the date column of the given dataframe to a datetime format, and then sorts by date. 
    """

    dataframe[data_column_name] = pd.to_datetime(dataframe[data_column_name], format=date_format)
    return dataframe.sort_values(by=data_column_name)

# ROLLING DATA
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

def add_rest_column(
        game_data: pd.DataFrame, 
        game_date_column: str, 
        group_by_id: str | None = None
        ) -> pd.DataFrame:
    """
    Adds rest column to the given game_data. 
    The given game_data must be sorted by game date. 
    If it is the first game that has ever been played, the value for 'rest' will be NaN.
    """

    game_dates = None
    if group_by_id:
        game_dates = game_data.groupby(group_by_id, sort=False)
    else:
        game_dates = game_data

    game_data[REST] = game_dates[game_date_column].diff().dt.days - 1
    return game_data

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

def add_total_rebounds_column(
        game_data: pd.DataFrame, 
        orb_column: str, 
        drb_column: str
        ) -> pd.DataFrame:
    orb = game_data[orb_column]
    drb = game_data[drb_column]
    game_data[REBOUNDS] = orb + drb
    return game_data

def add_possessions_column(
        team_game_data: pd.DataFrame, 
        fga_column: str, 
        fta_column: str, 
        orb_column: str, 
        tov_column: str
        ) -> pd.DataFrame:
    fga = team_game_data[fga_column]
    fta = team_game_data[fta_column]
    orb = team_game_data[orb_column]
    tov = team_game_data[tov_column]
    team_game_data[POSSESSIONS] = fga + (0.44 * fta) - orb + tov
    return team_game_data

def add_home_or_away_column(
        team_game_data: pd.DataFrame, 
        matchup_column: str
        ) -> pd.DataFrame:
    matchup = team_game_data[matchup_column]
    home_or_away = pd.Series(index=matchup.index, dtype='Int64')
    home_or_away[matchup.str.contains('@', regex=False, na=False)] = 1
    home_or_away[matchup.str.contains('vs.', regex=False, na=False)] = 0
    team_game_data[HOME_OR_AWAY] = home_or_away
    return team_game_data

def add_season_type_columns(
        team_game_data: pd.DataFrame,
        game_id_column: str
        ) -> pd.DataFrame:
    def _calculate_season_type_column(season_type_id: pd.Series, season_test_value: int) -> pd.Series:
        """
        Args: season_type_id must be a pd.Series consisting of one string per column where each string represents the season type.
        """

        return (season_type_id == str(season_test_value)).astype(int)
    season_type_id = team_game_data[game_id_column].astype(str).str[0]
    team_game_data[PRESEASON] = _calculate_season_type_column(season_type_id, 1)
    team_game_data[REGULAR_SEASON] = _calculate_season_type_column(season_type_id, 2)
    team_game_data[PLAYOFFS] = _calculate_season_type_column(season_type_id, 4)
    team_game_data[PLAY_IN] = _calculate_season_type_column(season_type_id, 5)
    return team_game_data

def convert_win_loss_to_integer(
        game_data: pd.DataFrame,
        win_loss_column: str
        ) -> pd.DataFrame:
    """
    Converts the given game_data's win/loss columnn from a string represenation to an interger representation.
    A value of 0 representing a loss, and a value of 1 representing a win.
    """

    game_data[win_loss_column] = (game_data[win_loss_column].astype(str) == 'W').astype(int)
    return game_data

# TODO: Add converters to per 36 minutes for stats

OPPONENT_PREFIX = 'OPP_'

def add_opponent_stat_columns(
        team_game_data: pd.DataFrame, 
        game_id_column: str, 
        team_id_column: str,
        non_required_opponent_categories: list[str] = []
        ) -> pd.DataFrame:
    opponent_stats = team_game_data.copy()

    if non_required_opponent_categories:
        opponent_stats = opponent_stats.drop(columns=non_required_opponent_categories, errors='ignore')

    opponent_column_names = {}
    for column_name in opponent_stats.columns:
        opponent_column_name = column_name
        if column_name != game_id_column:
            opponent_column_name = OPPONENT_PREFIX + opponent_column_name
        opponent_column_names[column_name] = opponent_column_name

    opponent_stats = opponent_stats.rename(columns=opponent_column_names)
    merged = team_game_data.merge(opponent_stats, on=game_id_column)
    merged = merged[merged[team_id_column] != merged[OPPONENT_PREFIX + team_id_column]]
    return merged