import pandas as pd
from typing import Any

from src.data_preparation.components.category import Category, DataType
from src.data_preparation.data_collection.databases import player_game_database, player_info_database, team_game_database

POINTS = Category('POINTS', DataType.INTEGER)
REBOUNDS = Category('REBOUNDS', DataType.INTEGER)
REST = Category('REST', DataType.INTEGER)
PACE = Category('PACE', DataType.INTEGER)

NBA_DATE_FORMAT = "%b %d, %Y"

def split_by_player(player_game_data: pd.DataFrame) -> dict[Any, pd.DataFrame]:
    return {player_id : player_dataframe for player_id, player_dataframe in player_game_data.groupby(player_game_database.PLAYER_ID.category_name)}

def split_by_team(team_game_data: pd.DataFrame) -> dict[Any, pd.DataFrame]:
    return {team_id : team_dataframe for team_id, team_dataframe in team_game_data.groupby(team_game_database.TEAM_ID.category_name)}

def sort_by_date(game_data: pd.DataFrame) -> pd.DataFrame:
    game_data[player_game_database.GAME_DATE.category_name] = pd.to_datetime(game_data[player_game_database.GAME_DATE.category_name], format=NBA_DATE_FORMAT)
    return game_data.sort_values(by=player_game_database.GAME_DATE.category_name)

def calculate_points_column(field_goals_made: pd.Series, three_pointers_made: pd.Series, free_throws_made: pd.Series) -> pd.Series:
    return (field_goals_made - three_pointers_made) * 2 + three_pointers_made * 3 + free_throws_made

def add_points_column(game_data: pd.DataFrame) -> pd.DataFrame:
    fgm = game_data[player_game_database.FIELD_GOALS_MADE.category_name]
    fg3m = game_data[player_game_database.THREE_POINTERS_MADE.category_name]
    ftm = game_data[player_game_database.FREE_THROWS_MADE.category_name]
    game_data[POINTS.category_name] = calculate_points_column(fgm, fg3m, ftm)
    return game_data

def calculate_total_rebounds(offensive_rebounds: pd.Series, defensive_rebounds: pd.Series) -> pd.Series:
    return offensive_rebounds + defensive_rebounds

def add_rebounds_column(game_data: pd.DataFrame) -> pd.DataFrame:
    orb = game_data[player_game_database.OFFENSIVE_REBOUNDS.category_name]
    drb = game_data[player_game_database.DEFENSIVE_REBOUNDS.category_name]
    game_data[REBOUNDS.category_name] = calculate_total_rebounds(orb, drb)
    return game_data

def add_rest_column(player_game_data: pd.DataFrame, sorted_by_game_date: bool = False) -> pd.DataFrame:
    if not sorted_by_game_date:
        player_game_data = sort_by_date(player_game_data)
    player_game_data[REST.category_name] = player_game_data.groupby(player_game_database.PLAYER_ID.category_name, sort=False)[player_game_database.GAME_DATE.category_name].diff().dt.days - 1
    return player_game_data

def calculate_pace(team_game_data: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame()

def get_teams_of_game(matchup: str) -> tuple[str, str]:
    return ('', '')

def get_opposing_team_of_game(matchup: str, team_id: str) -> str:
    return ''

def get_home_or_away(matchup: str, team_id: str) -> dict[str, str]:
    return {}