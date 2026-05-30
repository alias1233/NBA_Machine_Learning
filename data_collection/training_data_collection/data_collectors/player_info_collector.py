import pandas as pd

from ...nba_data import NBAData, NBADataUser
from ..database import Database, DataCollector, DatabaseLoader

FILEPATH = "databases/player_info.db"
NAME = "player_info"
RAW_CATEGORIES = [
    "PERSON_ID", "integer",
    "HEIGHT", "text",
    "WEIGHT", "integer",
    "POSITION", "text",
    "FROM_YEAR", "integer",
    "TO_YEAR", "integer",
]
database_loader = DatabaseLoader(FILEPATH, NAME, RAW_CATEGORIES)

def get_all_player_seasons():
    database = database_loader.create_database()
    data = database.query_all_SQL()
    players = []
    for player_data in data:
        players.append((player_data[0], player_data[4], player_data[5]))
    return players

# Handles Retrieving Player Information
class PlayerInfoCollector(DataCollector):

    def add_player_data(self, player_id: str):
        player_data: pd.DataFrame = NBAData.get_common_player_info(player_id)[0]
        for game in player_data.itertuples(index=False):
            data_dict = {cat: getattr(game, cat) for cat in database_loader.get_category_names()}
            self.database.add_value(data_dict)
    
    def fetch_data_user(self, **kwargs):
        use_id = input("Input whether to search for players by id or by full name: (i/n) ").capitalize() == 'I'
        while True:
            player_id = NBADataUser.get_player_id(use_id)
            if player_id is None:
                return
            self.add_player_data(player_id)
    
    def fetch_data_automatic(self, index: int, player_ids: list):
        self.add_player_data(player_ids[index])
        print(f"player_id: {player_ids[index]}")

if __name__ == "__main__":
    database = database_loader.create_database()
    database.create_database_with_user_prompt_self()
    player_info_collector = PlayerInfoCollector(database)

    players = NBAData.get_all_players()
    player_ids = []
    for player in players:
        player_ids.append(player['id'])
    player_info_collector.fetch_data(player_ids=player_ids)

    # Testing
    data = database.print_values(100)
    
    database.close()

RUNPATH = "data_collection.training_data_collection.data_collectors.player_info_collector"
CurrentIndex = 237