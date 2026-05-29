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
    def fetch_data(self):
        user_input = ""
        while user_input.capitalize() != 'Q':
            user_input = input("Input the player name or q to quit: ")


if __name__ == "__main__":
    player_data_collector = PlayerDataCollector(FILEPATH, NAME, CATEGORIES)
    player_data_collector.begin_fetch_data()

RUNPATH = "data_collection.training_data_collection.player_data_collection"