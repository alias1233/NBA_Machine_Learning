import pandas as pd
from typing import Any

from src.data_preparation.data_collection.databases import player_game_database, player_info_database, team_game_database
from src.data_preparation.components.database import Database, Category

PLAYER_INFO_DATABASE: Database = player_info_database.DATABASE
PLAYER_GAME_DATABASE: Database = player_game_database.DATABASE
TEAM_GAME_DATABASE: Database = team_game_database.DATABASE

def get_all_players_season_played_info() -> list:
    PLAYER_INFO_DATABASE.initialize_components()
    categories = [
        player_info_database.PLAYER_ID,
        player_info_database.FROM_YEAR,
        player_info_database.TO_YEAR
    ]
    data = PLAYER_INFO_DATABASE.query(categories=categories)
    PLAYER_INFO_DATABASE.close()
    return data

def query_database_dataframe(
        database: Database,
        SQL_condition: str | None = None, 
        condition_params: dict[Category, Any] | None = None, 
        categories: list[Category] | None = None, 
        limit: int | None = None
        ) -> pd.DataFrame:
    database.initialize_components()
    data = database.query_dataframe(SQL_condition=SQL_condition, condition_params=condition_params, categories=categories, limit=limit)
    database.close()
    return data

def get_all_players_info() -> pd.DataFrame:
    return query_database_dataframe(PLAYER_INFO_DATABASE)

def get_all_player_game_data() -> pd.DataFrame:
    return query_database_dataframe(PLAYER_GAME_DATABASE)

def get_all_team_game_data() -> pd.DataFrame:
    return query_database_dataframe(TEAM_GAME_DATABASE)

def get_player_info(player_id: str) -> pd.DataFrame:
    SQL_condition = f"{player_info_database.PLAYER_ID.category_name} = :{player_info_database.PLAYER_ID.category_name}"
    condition_params = {player_info_database.PLAYER_ID : player_id}
    return query_database_dataframe(PLAYER_INFO_DATABASE, SQL_condition=SQL_condition, condition_params=condition_params)

# TODO: Add an optional season parameter
def get_player_game_data(player_id: str) -> pd.DataFrame:
    SQL_condition = f"{player_game_database.PLAYER_ID.category_name} = :{player_game_database.PLAYER_ID.category_name}"
    condition_params = {player_game_database.PLAYER_ID : player_id}
    return query_database_dataframe(PLAYER_GAME_DATABASE, SQL_condition=SQL_condition, condition_params=condition_params)

# TODO: Add an optional season parameter
def get_team_game_data(team_id: str) -> pd.DataFrame:
    SQL_condition = f"{team_game_database.TEAM_ID.category_name} = :{team_game_database.TEAM_ID.category_name}"
    condition_params = {team_game_database.TEAM_ID : team_id}
    return query_database_dataframe(TEAM_GAME_DATABASE, SQL_condition=SQL_condition, condition_params=condition_params)

if __name__ == "__main__":
    print(get_player_info('203076'))