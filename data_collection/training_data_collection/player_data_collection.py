from data_collection.nba_data import NBAData
from .database import Database, DataCollector

FILEPATH = "databases/player_data.db"
NAME = "players"
CATEGORIES = [
    ('PPG', 'integer'),
    ('TEST', 'text')
]

# Handles Retrieving Player Data
class PlayerDataCollector(DataCollector):

    def add_player_data(self, player_id: str, season: int):
        print(f"ID: {player_id} SEASON: {season}")

    def add_player_data_range(self, player_id: str, start_season_year: int, end_season_year: int):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_player_data(player_id, start_season)
            start_season += 1

    def fetch_data_user(self, **kwargs):

        def get_player_id(use_id: bool):
            if use_id:
                player = input("Input the player id or q to quit: ")
                if player.capitalize() == "Q":
                    return None
                return player
            
            player = input("Input the player name or q to quit: ")
            if player.capitalize() == "Q":
                return None

            player_ids = NBAData.player_name_to_ids(player)
            while not player_ids:
                player = input("Player name does not correspond with a player. Input the player name or q to quit: ")
                if player.capitalize() == "Q":
                    return None
                player_ids = NBAData.player_name_to_ids(player)

            player_id = 0
            if len(player_ids) == 1:
                player_id = player_ids[0]
            else:
                id_index = -1
                while id_index < 0 or id_index >= len(player_ids):
                    print(player_ids)
                    id_index = int(input("Input the index of the id to use: "))
                player_id = player_ids[id_index]
            return player_id
        
        def get_season_range():
            start_season = input("Input the start season year: ")
            end_season = input("Input the end season year: ")
            return (int(start_season), int(end_season))

        use_id = input("Input whether to search for players by id or by full name: (i/n) ").capitalize() == 'I'
        while True:
            player_id = get_player_id(use_id)
            if player_id is None:
                return
            season_start, season_end = get_season_range()
            self.add_player_data_range(player_id, season_start, season_end)

    def fetch_data_automatic(self, index: int, players: list, seasons: list):
        pass


if __name__ == "__main__":
    player_data_collector = PlayerDataCollector(FILEPATH, NAME, CATEGORIES)
    player_data_collector.create_database()
    player_data_collector.fetch_data(print_database=True, players=['Lebron James'], seasons=[2020])

RUNPATH = "data_collection.training_data_collection.player_data_collection"