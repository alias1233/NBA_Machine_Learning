import pandas as pd

from ...nba_data import NBAData, NBADataUser
from .. import database
from ..database import Database, DatabaseLoader
from ..base_data_collector import DataCollector
from . import player_info_collector

FILEPATH = "databases/player_game_data.db"
NAME = "players"
RAW_CATEGORIES = [
    "Player_ID", "integer",
    "Game_ID", "integer",
    "GAME_DATE", "text",
    "MATCHUP", "text",
    "WL", "text",
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
    "PLUS_MINUS", "integer",
]
PRIMARY_KEYS = [
    "Player_ID",
    "Game_ID"
]
DATA_CONFLICT_HANDLER = database.DataConflictHandler.IGNORE
database_loader = DatabaseLoader(FILEPATH, NAME, RAW_CATEGORIES, DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Handles Retrieving Player Game Log Data
class PlayerDataCollector(DataCollector):

    def add_player_data(self, player_id: str, season: int):
        player_data: pd.DataFrame = NBAData.get_player_season_game_logs(player_id, season)[0]
        data = []
        for game in player_data.itertuples(index=False):
            data_dict = {cat: getattr(game, cat) for cat in database_loader.get_category_names()}
            data.append(data_dict)
        self.database.add_many_values(data)

    def add_player_data_range(self, player_id: str, start_season_year: int, end_season_year: int):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_player_data(player_id, start_season)
            start_season += 1

    def fetch_data_automatic(self, index: int, player_data: list) -> bool:
        if index >= len(player_data):
            return False
        player = player_data[index]
        self.add_player_data_range(player[0], player[1], player[2])
        
        print(f'Player ID: {player[0]} SEASON START: {player[1]} SEASON END: {player[2]}')

        return True

def collect_and_save_data(wait_interval: float, starting_index: int = 0, player_data: list = []):
    database = database_loader.create_database()
    database.create_database_self()

    if not player_data:
        player_info_collector.get_all_player_seasons()
        player_data = []
        try:
            player_data = player_info_collector.get_all_player_seasons()
        except:
            print("Database of player seasons is non-functional. Automatic data collection is non-functional.")

    player_data_collector = PlayerDataCollector(database)
    index = player_data_collector.begin_fetch_data(starting_index=starting_index, wait_interval=wait_interval, player_data=player_data)

    database.close()

    return index

if __name__ == "__main__":
    pass

RUNPATH = "data_collection.training_data_collection.data_collectors.player_game_data_collector"