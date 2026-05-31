import pandas as pd

from ...nba_data import NBAData, NBADataUser
from .. import database
from ..database import Database, DatabaseLoader
from ..base_data_collector import DataCollector

FILEPATH = "databases/team_game_data.db"
NAME = "teams"
RAW_CATEGORIES = [
    "Team_ID", "integer",
    "Game_ID", "integer",
    "GAME_DATE", "text",
    "MATCHUP", "text",
    "WL", "text",
    "W", "text",
    "L", "text",
    "W_PCT", "real",
    "MIN", "integer",
    "FGM", "integer",
    "FGA", "integer",
    "FG_PCT", "real",
    "FG3M", "integer",
    "FG3A", "integer",
    "FG3_PCT", "real",
    "FTM", "integer",
    "FTA", "integer",
    "FT_PCT", "real",
    "OREB", "integer",
    "DREB", "integer",
    "REB", "integer",
    "AST", "integer",
    "STL", "integer",
    "BLK", "integer",
    "TOV", "integer",
    "PF", "integer",
    "PTS", "integer",
]
PRIMARY_KEYS = [
    "Team_ID",
    "Game_ID"
]
DATA_CONFLICT_HANDLER = database.DataConflictHandler.IGNORE
database_loader = DatabaseLoader(FILEPATH, NAME, RAW_CATEGORIES, DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Handles Retrieving Team Data
class TeamDataCollector(DataCollector):

    def add_team_data(self, team_id: str, season: int):
        team_data: pd.DataFrame = NBAData.get_team_season_stats(team_id, season)[0]
        data = []
        for game in team_data.itertuples(index=False):
            data_dict = {cat : getattr(game, cat) for cat in database_loader.get_category_names()}
            data.append(data_dict)
        self.database.add_many_values(data)

    def add_team_data_range(self, team_id: str, start_season_year: int, end_season_year: int):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_team_data(team_id, start_season)
            start_season += 1

    def fetch_data_automatic(self, index: int, team_info: list) -> bool:
        return False
    
def collect_and_save_data(wait_interval: float, starting_index: int = 0, team_info: list = []):
    database = database_loader.create_database()
    database.create_database_self()

    if not team_info:
        pass

    team_data_collector = TeamDataCollector(database)
    index = team_data_collector.begin_fetch_data(starting_index=starting_index, wait_interval=wait_interval, team_info=team_info)

    database.close()

    return index

if __name__ == "__main__":
    pass

RUNPATH = "data_collection.training_data_collection.data_collectors.team_game_data_collector"