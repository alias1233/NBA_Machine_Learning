import pandas as pd
import time

from ..components.nba_data import NBAData
from ..components.base_data_collector import DataCollector
from ..databases.team_game_database import DATABASE

class TeamDameDataCollector(DataCollector):
    """
    Handles Retrieving Team Data
    """

    def add_team_data(self, team_id: str, season: int):
        data = NBAData.get_team_season_stats(team_id, season)
        if not data:
            return
        
        team_data: pd.DataFrame = data[0]
        data = []
        for game in team_data.itertuples(index=False):
            data_dict = {category : getattr(game, category.category_name) for category in DATABASE.get_categories()}
            data.append(data_dict)
        DATABASE.add_many_values(data)

    def add_team_data_range(self, team_id: str, start_season_year: int, end_season_year: int, wait_interval: float):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_team_data(team_id, start_season)
            start_season += 1
            time.sleep(wait_interval)

    def fetch_data_automatic(self, index: int, wait_interval: float, team_info: list) -> bool:
        if index >= len(team_info):
            return False
        
        team = team_info[index]
        self.add_team_data_range(team[0], team[1], team[2], wait_interval)
        
        return True