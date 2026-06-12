import pandas as pd
from pandas.core.window.rolling import Rolling
from typing import Any, Callable
from dataclasses import dataclass

# TODO: Fix errors concerning pandas: A value is trying to be set on a copy of a slice from a DataFrame.

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

# Represents the number of days without a game inbetween the current game and the player's last played game.
REST = 'REST'

def add_rest_column(
        game_data: pd.DataFrame, 
        game_date_column: str, 
        group_by_id: str | None = None
        ) -> pd.DataFrame:
    """
    Adds rest column to the given game_data. 
    The given game_data must be sorted by game date, and the game_date column must be in datetime form.
    If it is the first game that has ever been played, the value for 'rest' will be NaN.
    """

    game_dates = None
    if group_by_id:
        game_dates = game_data.groupby(group_by_id, sort=False)
    else:
        game_dates = game_data

    game_data[REST] = game_dates[game_date_column].diff().dt.days - 1
    return game_data

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


POSSESSIONS = 'POSSESSIONS'

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

# A value of 0 represents home, and a value of 1 represents away.
HOME_OR_AWAY = 'HOME_OR_AWAY'

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

def _add_time_between_static_player_event_and_game_column(
    game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_player_info: str,
    player_id_column_game_data: str,
    static_player_event_time_column: str,
    game_date_column: str,
    new_column_name: str,
    ) -> pd.DataFrame:
    """
    Adds a column to game_data representing the time elapsed between a static event's date and the current game date.
    The static event's dates are represented inside of a dataframe where each player_id corresponds to the static event's time.
    The static_player_event_time and game_date columns must be represented in datetime form.
    """

    TEMP = 'TEMP'

    player_id_to_static_event_time = player_info.set_index(player_id_column_player_info)[static_player_event_time_column].to_dict()
    game_data[TEMP] = game_data[player_id_column_game_data].map(player_id_to_static_event_time, na_action='ignore')
    game_data[new_column_name] = game_data[game_date_column] - game_data[TEMP]
    game_data = game_data.drop(columns=TEMP)
    return game_data

AGE_DURING_GAME = 'AGE_DURING_GAME'

def add_age_during_game_column(
    game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_player_info: str,
    player_id_column_game_data: str,
    birthdate_column: str,
    game_date_column: str
    ) -> pd.DataFrame:
    """
    The birthdate and game_date columns must be represented in datetime form.
    """

    return _add_time_between_static_player_event_and_game_column(
        game_data,
        player_info,
        player_id_column_player_info,
        player_id_column_game_data,
        birthdate_column,
        game_date_column,
        AGE_DURING_GAME
    )

NBA_EXPERIENCE_DURING_GAME = 'NBA_EXPERIENCE_DURING_GAME'

def add_NBA_experience_during_game_column(
    game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_player_info: str,
    player_id_column_game_data: str,
    date_entered_league_column: str,
    game_date_column: str
    ) -> pd.DataFrame:
    """
    The date_entered_league and game_date columns must be represented in datetime form.
    """

    return _add_time_between_static_player_event_and_game_column(
        game_data,
        player_info,
        player_id_column_player_info,
        player_id_column_game_data,
        date_entered_league_column,
        game_date_column,
        NBA_EXPERIENCE_DURING_GAME
    )

def _encode_string_equality_as_integer(column: pd.Series, string: str) -> pd.Series:
    """
    Returns a series where each value is 1 if the value corresponding to the given series equals the given string, and 0 otherwise.  
    """

    return (column == string).astype(int)

### SEASON TYPES: A value of 1 represents True, and a value of 0 represents False. ###
PRESEASON = 'PRESEASON'
REGULAR_SEASON = 'REGULAR_SEASON'
PLAYOFFS = 'PLAYOFFS'
PLAY_IN = 'PLAY_IN'

def add_season_type_columns(
        team_game_data: pd.DataFrame,
        game_id_column: str
        ) -> pd.DataFrame:
    season_type_id = team_game_data[game_id_column].astype(str).str[0]
    team_game_data[PRESEASON] = _encode_string_equality_as_integer(season_type_id, "1")
    team_game_data[REGULAR_SEASON] = _encode_string_equality_as_integer(season_type_id, "2")
    team_game_data[PLAYOFFS] = _encode_string_equality_as_integer(season_type_id, "4")
    team_game_data[PLAY_IN] = _encode_string_equality_as_integer(season_type_id, "5")
    return team_game_data

def convert_win_loss_to_integer(
        game_data: pd.DataFrame,
        win_loss_column: str
        ) -> pd.DataFrame:
    """
    Converts the given game_data's win/loss columnn from a string represenation to an interger representation.
    A value of 0 representing a loss, and a value of 1 representing a win.
    """

    game_data[win_loss_column] = _encode_string_equality_as_integer(game_data[win_loss_column], "W")
    return game_data

def convert_height_to_inches(
        player_info: pd.DataFrame,
        height_column: str
        ) -> pd.DataFrame:
    heights_split = player_info[height_column].str.split("-", expand=True)
    feet = pd.to_numeric(heights_split[0], errors="coerce")
    inches = pd.to_numeric(heights_split[1], errors="coerce")
    player_info[height_column] = feet * 12 + inches
    return player_info

### POSITION TYPES: A value of 1 represents True, and a value of 0 represents False. ###
CENTER = 'Center'
CENTER_FORWARD = 'Center-Forward'
FORWARD = 'Forward'
FORWARD_CENTER = 'Forward-Center'
FORWARD_GUARD = 'Forward-Guard'
GUARD = 'Guard'
GUARD_FORWARD = 'Guard-Forward'

def add_position_columns(
        player_info: pd.DataFrame,
        position_column: str,
        ) -> pd.DataFrame:
    position = player_info[position_column]
    player_info[CENTER] = _encode_string_equality_as_integer(position, CENTER)
    player_info[CENTER_FORWARD] = _encode_string_equality_as_integer(position, CENTER_FORWARD)
    player_info[FORWARD] = _encode_string_equality_as_integer(position, FORWARD)
    player_info[FORWARD_CENTER] = _encode_string_equality_as_integer(position, FORWARD_CENTER)
    player_info[FORWARD_GUARD] = _encode_string_equality_as_integer(position, FORWARD_GUARD)
    player_info[GUARD] = _encode_string_equality_as_integer(position, GUARD)
    player_info[GUARD_FORWARD] = _encode_string_equality_as_integer(position, GUARD_FORWARD)
    return player_info

def drop_all_rows_with_missing_info(
        data: pd.DataFrame
    ) -> pd.DataFrame:
    """
    Drops all rows with any columns containing exactly '' as its value.
    """

    return data[(data != '').all(axis=1)]
