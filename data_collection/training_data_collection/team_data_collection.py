from data_collection.nba_data import NBAData
from .database import Database, DataCollector

FILEPATH = "databases/team_data.db"
NAME = "teams"
CATEGORIES = [
    ('PPG', 'integer'),
    ('TEST', 'text')
]

# Handles Retrieving Team Data
class TeamDataCollector(DataCollector):
    def fetch_data(self):
        user_input = ""
        while user_input.capitalize() != 'Q':
            user_input = input("Input the team name or q to quit: ")


if __name__ == "__main__":
    team_data_collector = TeamDataCollector(FILEPATH, NAME, CATEGORIES)
    team_data_collector.begin_fetch_data()

RUNPATH = "data_collection.training_data_collection.team_data_collection"