from ...nba_data import NBAData
from ..database import Database, DataCollector

FILEPATH = "databases/team_data.db"
NAME = "teams"
CATEGORIES = [
    ('PPG', 'integer'),
    ('TEST', 'text')
]

# Handles Retrieving Team Data
class TeamDataCollector(DataCollector):

    def fetch_data_user(self, **kwargs):
        user_input = ""
        while user_input.capitalize() != 'Q':
            user_input = input("Input the team name or q to quit: ")

    def fetch_data_automatic(self, index: int, teams: list):
        pass


if __name__ == "__main__":
    Database.create_database_with_user_prompt(FILEPATH, NAME, CATEGORIES)
    database = Database(FILEPATH, NAME, CATEGORIES)
    team_data_collector = TeamDataCollector(database)
    team_data_collector.fetch_data()

RUNPATH = "data_collection.training_data_collection.data_collectors.team_game_data_collector"