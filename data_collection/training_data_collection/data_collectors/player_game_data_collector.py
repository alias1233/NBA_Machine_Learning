import pandas as pd

from ...nba_data import NBAData, NBADataUser
from ..database import Database, DataCollector, DatabaseLoader
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
database_loader = DatabaseLoader(FILEPATH, NAME, RAW_CATEGORIES)

# Handles Retrieving Player Game Log Data
class PlayerDataCollector(DataCollector):

    def add_player_data(self, player_id: str, season: int):
        player_data: pd.DataFrame = NBAData.get_player_season_game_logs(player_id, season)[0]
        for game in player_data.itertuples(index=False):
            data_dict = {cat: getattr(game, cat) for cat in database_loader.get_category_names()}
            self.database.add_value(data_dict)

    def add_player_data_range(self, player_id: str, start_season_year: int, end_season_year: int):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_player_data(player_id, start_season)
            start_season += 1

    def fetch_data_user(self, **kwargs):
        use_id = input("Input whether to search for players by id or by full name: (i/n) ").capitalize() == 'I'
        while True:
            player_id = NBADataUser.get_player_id_user(use_id)
            if player_id is None:
                return
            season_start, season_end = NBADataUser.get_season_range_user()
            self.add_player_data_range(player_id, season_start, season_end)

    def fetch_data_automatic(self, index: int, player_data: list) -> bool:
        if index >= len(player_data):
            return False
        player = player_data[index]
        self.add_player_data_range(player[0], player[1], player[2])
        
        print(f'Player ID: {player[0]} SEASON START: {player[1]} SEASON END: {player[2]}')

        return True


if __name__ == "__main__":
    database = database_loader.create_database()
    database.create_database_with_user_prompt_self()
    player_data_collector = PlayerDataCollector(database)

    player_data = []
    try:
        player_data = player_info_collector.get_all_player_seasons()
    except:
        print("Database of player seasons is non-functional. Automatic data collection is non-functional.")

    player_data_collector.fetch_data(player_data=player_data)

    # Testing
    player_name = input("Input the player name to query for: ")
    player_id = NBAData.player_name_to_ids(player_name)[0]
    data = database.query_condition_SQL(f"""Player_ID = {player_id}""")
    for row in data:
        print(row)
    
    database.close()

RUNPATH = "data_collection.training_data_collection.data_collectors.player_game_data_collector"