import pandas as pd

from src.data_preparation.components.nba_data import NBAData
from src.data_preparation.components.data_collector import DataCollector
from src.data_preparation.data_collection.databases import player_info_database

class PlayerInfoCollector(DataCollector):
    """
    Handles Retrieving Player Information
    """

    def _add_player_data(self, player_id: str):
        player_data: pd.DataFrame = NBAData.get_common_player_info(player_id)[0]
        for player in player_data.itertuples(index=False):
            data_dict = {category: getattr(player, category.category_name) for category in self.database.get_categories()}
            self.database.add_value(data_dict)
    
    def _collect_data(self, index: int, wait_interval: float, player_ids: list[str]) -> bool:
        if index >= len(player_ids):
            return False
        self._add_player_data(player_ids[index])

        print(f"player_id: {player_ids[index]}")

        return True
    
    def begin_collect_data(self, index: int, wait_interval: float, player_ids: list) -> int:
        """
        Args: player_ids must be a list where each element is: player_id
        """

        return self._begin_collect_data(index, wait_interval, player_ids=player_ids)
    
PLAYER_INFO_COLLECTOR = PlayerInfoCollector(player_info_database.DATABASE)