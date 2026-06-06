import pandas as pd
import time

from src.data_preparation.components.nba_data import NBAData
from src.data_preparation.components.data_collector import DataCollector
from src.data_preparation.data_collection.databases import team_game_database

class TeamDameDataCollector(DataCollector):
    """
    Handles Retrieving Team Data
    """

    def _add_team_data(self, team_id: str, season: int, season_type: str):
        data = NBAData.get_team_season_stats(team_id, season, season_type)
        if not data:
            return
        
        team_data: pd.DataFrame = data[0]
        data = []
        for game in team_data.itertuples(index=False):
            data_dict = {category : getattr(game, category.category_name) for category in self.database.get_categories()}
            data.append(data_dict)
        self.database.add_many_values(data)

    def _add_team_data_range(self, team_id: str, start_season_year: int, end_season_year: int, season_types: list[str], wait_interval: float):
        start_season = start_season_year
        while start_season <= end_season_year:
            for season_type in season_types:
                self._add_team_data(team_id, start_season, season_type)
                time.sleep(wait_interval)
            start_season += 1

    def _collect_data(self, index: int, wait_interval: float, team_info: list, season_types: list[str]) -> bool:
        if index >= len(team_info):
            return False
        
        team = team_info[index]
        self._add_team_data_range(team[0], team[1], team[2], season_types, wait_interval)
        
        return True
    
    def begin_collect_data(self, index: int, wait_interval: float, team_info: list, season_types: list[str]) -> int:
        """
        Args: team_info must be a list where each element is: (team_id, season_start, season_end)
        """

        return self._begin_collect_data(index, wait_interval, team_info=team_info, season_types=season_types)
    
TEAM_GAME_DATA_COLLECTOR = TeamDameDataCollector(team_game_database.DATABASE)