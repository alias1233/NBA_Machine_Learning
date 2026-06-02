import pandas as pd
import time

from ..components.nba_data import NBAData
from ..components.base_data_collector import DataCollector
from ..databases.player_game_database import DATABASE

class PlayerGameDataCollector(DataCollector):
    """
    Handles Retrieving Player Game Log Data
    """

    def add_player_data(self, player_id: str, season: int):
        data = NBAData.get_player_season_game_logs(player_id, season)
        if not data:
            return
        
        player_data: pd.DataFrame = data[0]
        data = []
        for game in player_data.itertuples(index=False):
            data_dict = {category: getattr(game, category.category_name) for category in DATABASE.get_categories()}
            data.append(data_dict)
        DATABASE.add_many_values(data)

    def add_player_data_range(self, player_id: str, start_season_year: int, end_season_year: int, wait_interval: float):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_player_data(player_id, start_season)
            start_season += 1
            time.sleep(wait_interval)

    def fetch_data_automatic(self, index: int, wait_interval: float, player_info: list) -> bool:
        if index >= len(player_info):
            return False
        player = player_info[index]
        self.add_player_data_range(player[0], player[1], player[2], wait_interval)
        
        print(f'Player ID: {player[0]} SEASON START: {player[1]} SEASON END: {player[2]}')

        return True