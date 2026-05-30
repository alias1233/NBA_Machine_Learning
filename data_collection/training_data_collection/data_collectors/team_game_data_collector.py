import pandas as pd

from ...nba_data import NBAData, NBADataUser
from ..database import Database, DataCollector, DatabaseLoader

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
database_loader = DatabaseLoader(FILEPATH, NAME, RAW_CATEGORIES)

# Handles Retrieving Team Data
class TeamDataCollector(DataCollector):

    def add_team_data(self, team_id: str, season: int):
        team_data: pd.DataFrame = NBAData.get_team_season_stats(team_id, season)[0]
        for game in team_data.itertuples(index=False):
            data_dict = {cat : getattr(game, cat) for cat in database_loader.get_category_names()}
            self.database.add_value(data_dict)

    def add_team_data_range(self, team_id: str, start_season_year: int, end_season_year: int):
        start_season = start_season_year
        while start_season <= end_season_year:
            self.add_team_data(team_id, start_season)
            start_season += 1

    def fetch_data_user(self, **kwargs):
        choose_schema: NBADataUser.TeamChooseSchema | None = None
        while choose_schema is None:
            choose_type = input("Input whether to search for teams by id, name, or abbreviation: (i/n/a) ")
            match choose_type.capitalize():
                case "I":
                    choose_schema = NBADataUser.TeamChooseSchema.ID
                case "N":
                    choose_schema = NBADataUser.TeamChooseSchema.FULL_NAME
                case "A":
                    choose_schema = NBADataUser.TeamChooseSchema.ABBREVIATION
                case _:
                    print("Not a valid choosing option.")
        
        while True:
            team_id = NBADataUser.get_team_id_user(choose_schema)
            if team_id is None:
                return
            season_start, season_end = NBADataUser.get_season_range_user()
            self.add_team_data_range(team_id, season_start, season_end)


    def fetch_data_automatic(self, index: int, teams: list, seasons: list) -> bool:
        return False


if __name__ == "__main__":
    database = database_loader.create_database()
    database.create_database_with_user_prompt_self()
    team_data_collector = TeamDataCollector(database)

    teams = NBAData.get_all_teams()
    team_ids = []
    for team in teams:
        team_ids.append(team['id'])
    
    team_data_collector.fetch_data(team_ids=team_ids)

    # Testing
    data = database.print_values(100)
    
    database.close()

RUNPATH = "data_collection.training_data_collection.data_collectors.team_game_data_collector"