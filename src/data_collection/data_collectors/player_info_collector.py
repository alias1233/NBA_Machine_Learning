import pandas as pd

from ..components.nba_data import NBAData
from ..components.base_data_collector import DataCollector
from ..databases.player_info_database import DATABASE

class PlayerInfoCollector(DataCollector):
    """
    Handles Retrieving Player Information
    """

    def add_player_data(self, player_id: str):
        player_data: pd.DataFrame = NBAData.get_common_player_info(player_id)[0]
        for player in player_data.itertuples(index=False):
            data_dict = {category: getattr(player, category.category_name) for category in DATABASE.get_categories()}
            DATABASE.add_value(data_dict)
    
    def fetch_data_automatic(self, index: int, wait_interval: float, player_ids: list) -> bool:
        if index >= len(player_ids):
            return False
        self.add_player_data(player_ids[index])

        print(f"player_id: {player_ids[index]}")

        return True