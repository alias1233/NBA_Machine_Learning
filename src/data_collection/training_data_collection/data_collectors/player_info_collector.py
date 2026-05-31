import pandas as pd

from ...nba_data import NBAData, NBADataUser
from .. import database
from ..database import Database, DatabaseLoader
from ..base_data_collector import DataCollector

FILEPATH = "databases/player_info.db"
NAME = "player_info"
RAW_CATEGORIES = [
    "PERSON_ID", "integer",
    "HEIGHT", "text",
    "WEIGHT", "integer",
    "POSITION", "text",
    "FROM_YEAR", "integer",
    "TO_YEAR", "integer",
]
PRIMARY_KEYS = [
    "PERSON_ID"
]
DATA_CONFLICT_HANDLER = database.DataConflictHandler.REPLACE
database_loader = DatabaseLoader(FILEPATH, NAME, RAW_CATEGORIES, DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

def get_all_player_seasons():
    database = database_loader.create_database()
    data = database.query_all_SQL()
    players = [(player_data[0], player_data[4], player_data[5]) for player_data in data]
    return players

# Handles Retrieving Player Information
class PlayerInfoCollector(DataCollector):

    def add_player_data(self, player_id: str):
        player_data: pd.DataFrame = NBAData.get_common_player_info(player_id)[0]
        for player in player_data.itertuples(index=False):
            data_dict = {cat: getattr(player, cat) for cat in database_loader.get_category_names()}
            self.database.add_value(data_dict)
    
    def fetch_data_automatic(self, index: int, wait_interval: float, player_ids: list) -> bool:
        if index >= len(player_ids):
            return False
        self.add_player_data(player_ids[index])

        print(f"player_id: {player_ids[index]}")

        return True
    
def collect_and_save_data(wait_interval: float, starting_index: int = 0, player_ids: list = []):
    database = database_loader.create_database()
    database.create_database_self()

    if not player_ids:
        players = NBAData.get_all_players()
        player_ids = [player['id'] for player in players]

    player_info_collector = PlayerInfoCollector(database)
    index = player_info_collector.begin_fetch_data(starting_index=starting_index, wait_interval=wait_interval, player_ids=player_ids)

    database.close()

    return index

if __name__ == "__main__":
    pass

RUNPATH = "data_collection.training_data_collection.data_collectors.player_info_collector"
CURRENT_INDEX = 0