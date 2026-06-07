import pandas as pd
import time

from src.data_preparation.components.nba_data import NBAData
from src.data_preparation.components.data_collector import DataCollector
from src.data_preparation.data_collection.databases import team_game_database

class TeamDameDataCollector(DataCollector):
    """
    Handles Retrieving Team Data
    """

    def _add_season_game_data(self, season: int, season_type: str):
        data = NBAData.get_all_teams_season_game_logs(season, season_type)
        if not data:
            return
        
        team_data: pd.DataFrame = data[0]
        data = []
        for game in team_data.itertuples(index=False):
            data_dict = {category : getattr(game, category.category_name) for category in self.database.get_categories()}
            data.append(data_dict)
        self.database.add_many_values(data)

    def _add_season_game_data_range(self, season: int, season_types: list[str], wait_interval: float):
        for season_type in season_types:
                self._add_season_game_data(season, season_type)
                time.sleep(wait_interval)

    def _collect_data(self, index: int, wait_interval: float, seasons: list[int], season_types: list[str]) -> bool:
        if index >= len(seasons):
            return False
        
        season = seasons[index]
        self._add_season_game_data_range(season, season_types, wait_interval)

        print(f'SEASON YEAR: {season} SEASON TYPES: {season_types}')
        
        return True
    
    def begin_collect_data(self, index: int, wait_interval: float, seasons: list[int], season_types: list[str]) -> int:
        """
        Args: seasons must be the list of seasons to query from, and season_types are the list of season types to query from.
        """

        return self._begin_collect_data(index, wait_interval, seasons=seasons, season_types=season_types)
    
TEAM_GAME_DATA_COLLECTOR = TeamDameDataCollector(team_game_database.DATABASE)