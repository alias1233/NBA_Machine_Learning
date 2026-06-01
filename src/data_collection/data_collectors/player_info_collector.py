import pandas as pd

from .components.nba_data import NBAData
from .components import database
from .components.database import Database, Categories, DataType
from .base_data_collector import DataCollector

FILEPATH = "databases/player_info.db"
NAME = "player_info"
CATEGORIES = Categories()
PLAYER_ID = CATEGORIES.add_category("PERSON_ID", DataType.INTEGER)
HEIGHT = CATEGORIES.add_category("HEIGHT", DataType.INTEGER)
WEIGHT = CATEGORIES.add_category("WEIGHT", DataType.REAL)
POSITION = CATEGORIES.add_category("POSITION", DataType.TEXT)
FROM_YEAR = CATEGORIES.add_category("FROM_YEAR", DataType.INTEGER)
TO_YEAR = CATEGORIES.add_category("TO_YEAR", DataType.INTEGER)
PRIMARY_KEYS = [
    PLAYER_ID
]
DATA_CONFLICT_HANDLER = database.DataConflictHandler.REPLACE
DATABASE = Database(FILEPATH, NAME, CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Handles Retrieving Player Information
class PlayerInfoCollector(DataCollector):

    def add_player_data(self, player_id: str):
        player_data: pd.DataFrame = NBAData.get_common_player_info(player_id)[0]
        for player in player_data.itertuples(index=False):
            data_dict = {cat: getattr(player, cat) for cat in self.database.get_category_names()}
            self.database.add_value(data_dict)
    
    def fetch_data_automatic(self, index: int, wait_interval: float, player_ids: list) -> bool:
        if index >= len(player_ids):
            return False
        self.add_player_data(player_ids[index])

        print(f"player_id: {player_ids[index]}")

        return True
    
def collect_and_save_data(wait_interval: float, starting_index: int, player_ids: list):
    DATABASE.initialize_components()
    DATABASE.create_database_self()

    player_info_collector = PlayerInfoCollector(DATABASE)
    index = player_info_collector.begin_fetch_data(starting_index=starting_index, wait_interval=wait_interval, player_ids=player_ids)

    DATABASE.close()

    return index

if __name__ == "__main__":
    pass

RUNPATH = "data_collection.training_data_collection.data_collectors.player_info_collector"
CURRENT_INDEX = 0