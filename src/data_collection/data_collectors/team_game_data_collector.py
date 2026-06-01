import pandas as pd
import time

from .components.nba_data import NBAData
from .components import database
from .components.database import Database, Categories, DataType
from .base_data_collector import DataCollector

FILEPATH = "databases/team_game_data.db"
NAME = "teams"
CATEGORIES = Categories()
TEAM_ID = CATEGORIES.add_category("Team_ID", DataType.INTEGER)
GAME_ID = CATEGORIES.add_category("Game_ID", DataType.INTEGER)
GAME_DATE = CATEGORIES.add_category("GAME_DATE", DataType.TEXT)
MATCHUP = CATEGORIES.add_category("MATCHUP", DataType.TEXT)
WIN_LOSS = CATEGORIES.add_category("WL", DataType.TEXT)
CURRENT_SEASON_WINS = CATEGORIES.add_category("W", DataType.TEXT)
CURRENT_SEASON_LOSSES = CATEGORIES.add_category("L", DataType.TEXT)
MINUTES_PLAYED = CATEGORIES.add_category("MIN", DataType.INTEGER)
FIELD_GOALS_MADE = CATEGORIES.add_category("FGM", DataType.INTEGER)
FIELD_GOALS_ATTEMPTED = CATEGORIES.add_category("FGA", DataType.INTEGER)
THREE_POINTERS_MADE = CATEGORIES.add_category("FG3M", DataType.INTEGER)
THREE_POINTERS_ATTEMPTED = CATEGORIES.add_category("FG3A", DataType.INTEGER)
FREE_THROWS_MADE = CATEGORIES.add_category("FTM", DataType.INTEGER)
FREE_THROWS_ATTEMPTED = CATEGORIES.add_category("FTA", DataType.INTEGER)
OFFENSIVE_REBOUNDS = CATEGORIES.add_category("OREB", DataType.INTEGER)
DEFENSIVE_REBOUNDS = CATEGORIES.add_category("DREB", DataType.INTEGER)
ASSISTS = CATEGORIES.add_category("AST", DataType.INTEGER)
STEALS = CATEGORIES.add_category("STL", DataType.INTEGER)
BLOCKS = CATEGORIES.add_category("BLK", DataType.INTEGER)
TURNOVERS = CATEGORIES.add_category("TOV", DataType.INTEGER)
PERSONAL_FOULS = CATEGORIES.add_category("PF", DataType.INTEGER)
PLUS_MINUS = CATEGORIES.add_category("PLUS_MINUS", DataType.INTEGER)
# TODO: Add pace/possessions as a property from leaguedashteamstats
PRIMARY_KEYS = [
    TEAM_ID,
    GAME_ID
]
DATA_CONFLICT_HANDLER = database.DataConflictHandler.IGNORE
DATABASE = Database(FILEPATH, NAME, CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Handles Retrieving Team Data
class TeamDataCollector(DataCollector):

    def add_team_data(self, team_id: str, season: int):
        team_data: pd.DataFrame = NBAData.get_team_season_stats(team_id, season)[0]
        data = []
        for game in team_data.itertuples(index=False):
            data_dict = {cat : getattr(game, cat) for cat in self.database.get_category_names()}
            data.append(data_dict)
        self.database.add_many_values(data)

    def add_team_data_range(self, team_id: str, start_season_year: int, end_season_year: int, wait_interval: float):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_team_data(team_id, start_season)
            start_season += 1
            time.sleep(wait_interval)

    def fetch_data_automatic(self, index: int, wait_interval: float, team_info: list) -> bool:
        return False
    
def collect_and_save_data(wait_interval: float, starting_index: int, team_info: list):
    DATABASE.initialize_components()
    DATABASE.create_database_self()

    team_data_collector = TeamDataCollector(DATABASE)
    index = team_data_collector.begin_fetch_data(starting_index=starting_index, wait_interval=wait_interval, team_info=team_info)

    DATABASE.close()

    return index

if __name__ == "__main__":
    pass

RUNPATH = "data_collection.training_data_collection.data_collectors.team_game_data_collector"