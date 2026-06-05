import pandas as pd
import time

from src.data_preparation.components.nba_data import NBAData
from src.data_preparation.components.data_collector import DataCollector
from src.data_preparation.data_collection.databases import player_game_database

class PlayerGameDataCollector(DataCollector):
    """
    Handles Retrieving Player Game Log Data
    """

    def _add_player_data(self, player_id: str, season: int):
        data = NBAData.get_player_season_game_logs(player_id, season)
        if not data:
            return
        
        player_data: pd.DataFrame = data[0]
        data = []
        for game in player_data.itertuples(index=False):
            data_dict = {category: getattr(game, category.category_name) for category in self.database.get_categories()}
            data.append(data_dict)
        self.database.add_many_values(data)

    def _add_player_data_range(self, player_id: str, start_season_year: int, end_season_year: int, wait_interval: float):
        start_season = start_season_year
        while start_season <= end_season_year:
            self._add_player_data(player_id, start_season)
            start_season += 1
            time.sleep(wait_interval)

    def _collect_data(self, index: int, wait_interval: float, player_info: list) -> bool:
        if index >= len(player_info):
            return False
        player = player_info[index]
        self._add_player_data_range(player[0], player[1], player[2], wait_interval)
        
        print(f'Player ID: {player[0]} SEASON START: {player[1]} SEASON END: {player[2]}')

        return True
    
    def begin_collect_data(self, index: int, wait_interval: float, player_info: list) -> int:
        """
        Args: player_info must be a list where each element is: (player_id, start_season, end_season) 
        """

        return self._begin_collect_data(index, wait_interval, player_info=player_info)
    
PLAYER_GAME_DATA_COLLECTOR = PlayerGameDataCollector(player_game_database.DATABASE)