import pandas as pd
import time

from .components.nba_data import NBAData
from .components import database
from .components.database import Database, Categories, DataType
from .base_data_collector import DataCollector

FILEPATH = "databases/player_game_data.db"
NAME = "players"
CATEGORIES = Categories()
PLAYER_ID = CATEGORIES.add_category("Player_ID", DataType.INTEGER)
GAME_ID = CATEGORIES.add_category("Game_ID", DataType.INTEGER)
GAME_DATE = CATEGORIES.add_category("GAME_DATE", DataType.TEXT)
MATCHUP = CATEGORIES.add_category("MATCHUP", DataType.TEXT)
WIN_LOSS = CATEGORIES.add_category("WL", DataType.TEXT)
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
PRIMARY_KEYS = [
    PLAYER_ID,
    GAME_ID
]
DATA_CONFLICT_HANDLER = database.DataConflictHandler.IGNORE
DATABASE = Database(FILEPATH, NAME, CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Handles Retrieving Player Game Log Data
class PlayerDataCollector(DataCollector):

    def add_player_data(self, player_id: str, season: int):
        data = NBAData.get_player_season_game_logs(player_id, season)
        if not data:
            return
        
        player_data: pd.DataFrame = data[0]
        data = []
        for game in player_data.itertuples(index=False):
            data_dict = {cat: getattr(game, cat) for cat in self.database.get_category_names()}
            data.append(data_dict)
        self.database.add_many_values(data)

    def add_player_data_range(self, player_id: str, start_season_year: int, end_season_year: int, wait_interval: float):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_player_data(player_id, start_season)
            start_season += 1
            time.sleep(wait_interval)

    def fetch_data_automatic(self, index: int, wait_interval: float, player_data: list) -> bool:
        if index >= len(player_data):
            return False
        player = player_data[index]
        self.add_player_data_range(player[0], player[1], player[2], wait_interval)
        
        print(f'Player ID: {player[0]} SEASON START: {player[1]} SEASON END: {player[2]}')

        return True

def collect_and_save_data(wait_interval: float, starting_index: int, player_data: list):
    DATABASE.initialize_components()
    DATABASE.create_database_self()

    player_data_collector = PlayerDataCollector(DATABASE)
    index = player_data_collector.begin_fetch_data(starting_index=starting_index, wait_interval=wait_interval, player_data=player_data)

    DATABASE.close()

    return index

if __name__ == "__main__":
    pass

RUNPATH = "data_collection.training_data_collection.data_collectors.player_game_data_collector"