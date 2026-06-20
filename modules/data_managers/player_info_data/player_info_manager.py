# Categories
from src.data_preparation.category import DataType, Categories

ALL_CATEGORIES = Categories()
PLAYER_ID = ALL_CATEGORIES.add_category("PERSON_ID", DataType.INTEGER)
HEIGHT = ALL_CATEGORIES.add_category("HEIGHT", DataType.INTEGER)
WEIGHT = ALL_CATEGORIES.add_category("WEIGHT", DataType.REAL)
POSITION = ALL_CATEGORIES.add_category("POSITION", DataType.TEXT)
FROM_YEAR = ALL_CATEGORIES.add_category("FROM_YEAR", DataType.INTEGER)
TO_YEAR = ALL_CATEGORIES.add_category("TO_YEAR", DataType.INTEGER)
BIRTHDATE = ALL_CATEGORIES.add_category("BIRTHDATE", DataType.TEXT)
DRAFT_NUMBER = ALL_CATEGORIES.add_category("DRAFT_NUMBER", DataType.INTEGER)

# Database
from src.data_preparation.database import Database, DataConflictHandler
from modules.data_managers import directories

FILEPATH = directories.DATABASE_DIRECTORY + "player_info.db"
NAME = "player_info"
PRIMARY_KEYS = [
    PLAYER_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

DATABASE = Database(FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Collection
import time
import pandas as pd

from nba_api.stats.endpoints.commonplayerinfo import CommonPlayerInfo
from nba_api.stats.library.parameters import PlayerOrTeamAbbreviation
from src.data_preparation.repeater import repeater
from src.data_preparation.nba_data import NBAData, retry

@retry
def get_common_player_info(player_id: str) -> pd.DataFrame:
    return CommonPlayerInfo(
        player_id=player_id
    ).get_data_frames()[0]

def collect_player_info_data(
        wait_interval: float, 
        starting_index: int, 
        player_ids: list = []
        ) -> int:

    # If no parameters are given, use every player's ids.
    if not player_ids:
        players = NBAData.get_all_players()
        player_ids = [player['id'] for player in players]

    def _add_player_data(player_id: str):
        player_data: pd.DataFrame = get_common_player_info(player_id)

        for player in player_data.itertuples(index=False):
            data_dict = {category: getattr(player, category.category_name) for category in DATABASE.get_categories()}

            DATABASE.add_value(data_dict)
    
    def _collect_data(index: int) -> bool:
        if index >= len(player_ids):
            return False
        
        _add_player_data(player_ids[index])

        print(f"player_id: {player_ids[index]}")

        return True

    with DATABASE:
        index_reached = repeater(
            _collect_data,
            starting_index,
            wait_interval
        )
    
    return index_reached

# Query
def get_all_players_info() -> pd.DataFrame:
    with DATABASE:
        data = DATABASE.query_dataframe()

    return data

def get_player_info(player_id: str) -> pd.DataFrame:
    SQL_condition = f"{PLAYER_ID.category_name} = :{PLAYER_ID.category_name}"
    condition_params = {PLAYER_ID : player_id}

    with DATABASE:
        data = DATABASE.query_dataframe(
            SQL_condition=SQL_condition, 
            condition_params=condition_params
        )

    return data