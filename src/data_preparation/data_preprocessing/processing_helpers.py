import pandas as pd
from pandas.core.window.rolling import Rolling
from typing import Any, Callable
from dataclasses import dataclass

from src.data_preparation.components.category import Category, DataType
from src.data_preparation.data_collection.databases import player_game_database, player_info_database, team_game_database

POINTS = Category('POINTS', DataType.INTEGER)
REBOUNDS = Category('REBOUNDS', DataType.INTEGER)

# Represents the number of days without a game inbetween the current game and the player's last played game.
REST = Category('REST', DataType.INTEGER)

POSSESSIONS = Category('POSSESSIONS', DataType.REAL)

# A value of 0 represents home, and a value of 1 represents away.
HOME_OR_AWAY = Category('HOME_OR_AWAY', DataType.INTEGER)

### SEASON TYPES: A value of 1 represents True, and a value of 0 represents False. ###
PRESEASON = Category('PRESEASON', DataType.INTEGER)
REGULAR_SEASON = Category('REGULAR_SEASON', DataType.INTEGER)
PLAYOFFS = Category('PLAYOFFS', DataType.INTEGER)
PLAY_IN = Category('PLAY_IN', DataType.INTEGER)

def split_by_category(data: pd.DataFrame, category_name: str) -> dict[Any, pd.DataFrame]:
    return {id : dataframe for id, dataframe in data.groupby(category_name)}

def split_by_player(player_game_data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return split_by_category(player_game_data, player_game_database.PLAYER_ID.category_name)

def split_by_team(team_game_data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return split_by_category(team_game_data, team_game_database.TEAM_ID.category_name)

def sort_games_by_date(game_data: pd.DataFrame, date_format: str | None = None) -> pd.DataFrame:
    game_data[player_game_database.GAME_DATE.category_name] = pd.to_datetime(game_data[player_game_database.GAME_DATE.category_name], format=date_format)
    return game_data.sort_values(by=player_game_database.GAME_DATE.category_name)

@dataclass
class RollingCategory():
    name: str
    calculated_from_category_name: str
    window_length: int
    exclusive: bool
    rolling_function: Callable[[Rolling], pd.Series]

MEAN_FUNCTION: Callable[[Rolling], pd.Series] = lambda x : x.mean()
STD_FUNCTION: Callable[[Rolling], pd.Series] = lambda x : x.std()

def _calculate_rolling_function_column(dataframe: pd.DataFrame, rolling_param: RollingCategory) -> pd.Series:
    calculated_from_column = dataframe[rolling_param.calculated_from_category_name]
    if rolling_param.exclusive:
        calculated_from_column = calculated_from_column.shift(1)
    return rolling_param.rolling_function(calculated_from_column.rolling(window=rolling_param.window_length))

def add_rolling_function_column(dataframe: pd.DataFrame, rolling_params: list[RollingCategory]) -> pd.DataFrame:
    """
    Computes rolling functions on the given dataframe. 
    """

    for rolling_param in rolling_params:
        dataframe[rolling_param.name] = _calculate_rolling_function_column(dataframe, rolling_param)

    return dataframe

def add_rest_column(player_game_data: pd.DataFrame, sorted_by_game_date: bool = False, grouped_by_player_id: bool = False) -> pd.DataFrame:
    """
    Adds rest column to the given player_game_data dataframe. If it is the first game that a player has ever played, the value for rest will be NaN.
    """

    if not sorted_by_game_date:
        player_game_data = sort_games_by_date(player_game_data)
    if not grouped_by_player_id:
        player_game_data[REST.category_name] = player_game_data.groupby(player_game_database.PLAYER_ID.category_name, sort=False)[player_game_database.GAME_DATE.category_name].diff().dt.days - 1
    else:
        player_game_data[REST.category_name] = player_game_data[player_game_database.GAME_DATE.category_name].diff().dt.days - 1
    return player_game_data

def _calculate_points_column(field_goals_made: pd.Series, three_pointers_made: pd.Series, free_throws_made: pd.Series) -> pd.Series:
    return (field_goals_made - three_pointers_made) * 2 + three_pointers_made * 3 + free_throws_made

def add_points_column(game_data: pd.DataFrame) -> pd.DataFrame:
    fgm = game_data[player_game_database.FIELD_GOALS_MADE.category_name]
    fg3m = game_data[player_game_database.THREE_POINTERS_MADE.category_name]
    ftm = game_data[player_game_database.FREE_THROWS_MADE.category_name]
    game_data[POINTS.category_name] = _calculate_points_column(fgm, fg3m, ftm)
    return game_data

def _calculate_total_rebounds_column(offensive_rebounds: pd.Series, defensive_rebounds: pd.Series) -> pd.Series:
    return offensive_rebounds + defensive_rebounds

def add_rebounds_column(game_data: pd.DataFrame) -> pd.DataFrame:
    orb = game_data[player_game_database.OFFENSIVE_REBOUNDS.category_name]
    drb = game_data[player_game_database.DEFENSIVE_REBOUNDS.category_name]
    game_data[REBOUNDS.category_name] = _calculate_total_rebounds_column(orb, drb)
    return game_data

def _calculate_possessions_column(field_goals_attempted: pd.Series, free_throws_attempted: pd.Series, offensive_rebounds: pd.Series, turnovers: pd.Series) -> pd.Series:
    return field_goals_attempted + (0.44 * free_throws_attempted) - offensive_rebounds + turnovers

def add_possessions_column(team_game_data: pd.DataFrame) -> pd.DataFrame:
    fga = team_game_data[team_game_database.FIELD_GOALS_ATTEMPTED.category_name]
    fta = team_game_data[team_game_database.FREE_THROWS_ATTEMPTED.category_name]
    orb = team_game_data[team_game_database.OFFENSIVE_REBOUNDS.category_name]
    tov = team_game_data[team_game_database.TURNOVERS.category_name]
    team_game_data[POSSESSIONS.category_name] = _calculate_possessions_column(fga, fta, orb, tov)
    return team_game_data

def _calculate_home_or_away_column(matchup: pd.Series) -> pd.Series:
    home_or_away = pd.Series(index=matchup.index, dtype='Int64')
    home_or_away[matchup.str.contains('@', regex=False, na=False)] = 1
    home_or_away[matchup.str.contains('vs.', regex=False, na=False)] = 0
    return home_or_away

def add_home_or_away_column(team_game_data: pd.DataFrame) -> pd.DataFrame:
    matchup = team_game_data[team_game_database.MATCHUP.category_name]
    team_game_data[HOME_OR_AWAY.category_name] = _calculate_home_or_away_column(matchup)
    return team_game_data

def _calculate_season_type_column(season_type_id: pd.Series, season_test_value: int) -> pd.Series:
    """
    Args: season_type_id must be a pd.Series consisting of one string per column where each string represents the season type.
    """

    return (season_type_id == str(season_test_value)).astype(int)

def add_season_type_columns(team_game_data: pd.DataFrame) -> pd.DataFrame:
    season_type_id = team_game_data[team_game_database.GAME_ID.category_name].astype(str).str[0]
    team_game_data[PRESEASON.category_name] = _calculate_season_type_column(season_type_id, 1)
    team_game_data[REGULAR_SEASON.category_name] = _calculate_season_type_column(season_type_id, 2)
    team_game_data[PLAYOFFS.category_name] = _calculate_season_type_column(season_type_id, 4)
    team_game_data[PLAY_IN.category_name] = _calculate_season_type_column(season_type_id, 5)
    return team_game_data

OPPONENT_PREFIX = 'OPP_'
NON_REQUIRED_OPPONENT_CATEGORY_NAMES = [
    team_game_database.GAME_DATE.category_name,
    team_game_database.WIN_LOSS.category_name,
    team_game_database.MATCHUP.category_name,
    team_game_database.MINUTES_PLAYED.category_name,
    HOME_OR_AWAY.category_name,
    PRESEASON.category_name,
    REGULAR_SEASON.category_name,
    PLAYOFFS.category_name,
    PLAY_IN.category_name
]

def add_opponent_stat_columns(team_game_data: pd.DataFrame) -> pd.DataFrame:
    opponent_stats = team_game_data.copy()
    opponent_stats = opponent_stats.drop(columns=NON_REQUIRED_OPPONENT_CATEGORY_NAMES, errors='ignore')

    opponent_column_names = {}
    for column_name in opponent_stats.columns:
        opponent_column_name = column_name
        if column_name != team_game_database.GAME_ID.category_name:
            opponent_column_name = OPPONENT_PREFIX + opponent_column_name
        opponent_column_names[column_name] = opponent_column_name

    opponent_stats = opponent_stats.rename(columns=opponent_column_names)
    merged = team_game_data.merge(opponent_stats, on=team_game_database.GAME_ID.category_name)
    merged = merged[merged[team_game_database.TEAM_ID.category_name] != merged[OPPONENT_PREFIX + team_game_database.TEAM_ID.category_name]]
    return merged