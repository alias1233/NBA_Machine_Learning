# Categories
from src.data_preparation.category import DataType, Categories

ALL_CATEGORIES = Categories()
TEAM_ID = ALL_CATEGORIES.add_category("TEAM_ID", DataType.INTEGER)
GAME_ID = ALL_CATEGORIES.add_category("GAME_ID", DataType.INTEGER)
GAME_DATE = ALL_CATEGORIES.add_category("GAME_DATE", DataType.TEXT)
MATCHUP = ALL_CATEGORIES.add_category("MATCHUP", DataType.TEXT)
WIN_LOSS = ALL_CATEGORIES.add_category("WL", DataType.TEXT)
MINUTES_PLAYED = ALL_CATEGORIES.add_category("MIN", DataType.INTEGER)
FIELD_GOALS_MADE = ALL_CATEGORIES.add_category("FGM", DataType.INTEGER)
FIELD_GOALS_ATTEMPTED = ALL_CATEGORIES.add_category("FGA", DataType.INTEGER)
THREE_POINTERS_MADE = ALL_CATEGORIES.add_category("FG3M", DataType.INTEGER)
THREE_POINTERS_ATTEMPTED = ALL_CATEGORIES.add_category("FG3A", DataType.INTEGER)
FREE_THROWS_MADE = ALL_CATEGORIES.add_category("FTM", DataType.INTEGER)
FREE_THROWS_ATTEMPTED = ALL_CATEGORIES.add_category("FTA", DataType.INTEGER)
OFFENSIVE_REBOUNDS = ALL_CATEGORIES.add_category("OREB", DataType.INTEGER)
DEFENSIVE_REBOUNDS = ALL_CATEGORIES.add_category("DREB", DataType.INTEGER)
ASSISTS = ALL_CATEGORIES.add_category("AST", DataType.INTEGER)
STEALS = ALL_CATEGORIES.add_category("STL", DataType.INTEGER)
BLOCKS = ALL_CATEGORIES.add_category("BLK", DataType.INTEGER)
TURNOVERS = ALL_CATEGORIES.add_category("TOV", DataType.INTEGER)
PERSONAL_FOULS = ALL_CATEGORIES.add_category("PF", DataType.INTEGER)

# Database
from src.data_preparation.database import Database, DataConflictHandler

FILEPATH = "data/team_game_data.db"
NAME = "teams"
PRIMARY_KEYS = [
    TEAM_ID,
    GAME_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

DATABASE = Database(FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Collection
import time
import pandas as pd

from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog
from src.data_preparation.repeater import repeater
from src.data_preparation.nba_data import NBAData, retry

@retry
def get_all_teams_season_game_logs(
    season_year: int, 
    season_type: str
    ) -> pd.DataFrame | None:
    try:
        return LeagueGameLog(
            season=NBAData.convert_year_to_NBA_season(season_year),
            season_type_all_star=season_type
        ).get_data_frames()[0]
    except Exception as e:
        print(f"The year {season_year} with {season_type} season type is invalid")
        print(f"Error Message: {e}")

def collect_team_game_data(
        wait_interval: float, 
        starting_index: int, 
        seasons: list[int] = [], 
        season_types: list[str] = []
        ) -> int:

    # If no parameters are given, then use values for retreiving all games over all seasons.
    if not seasons:
        seasons = [i for i in range(NBAData.get_oldest_season_with_all_player_box_score_data_data(), NBAData.get_current_nba_season() + 1)]
    if not season_types:
        season_types = NBAData.get_all_season_types()

    def _add_season_game_data(season: int, season_type: str):
        team_game_data = get_all_teams_season_game_logs(season, season_type)
        if team_game_data is None:
            return
        
        data = []
        for game in team_game_data.itertuples(index=False):
            data_dict = {category : getattr(game, category.category_name) for category in DATABASE.get_categories()}

            data.append(data_dict)

        DATABASE.add_many_values(data)

    def _add_season_game_data_range(season: int):
        for season_type in season_types:
                _add_season_game_data(season, season_type)

                time.sleep(wait_interval)

    def _collect_data(index: int) -> bool:
        if index >= len(seasons):
            return False
        
        season = seasons[index]
        _add_season_game_data_range(season)

        print(f'SEASON YEAR: {season} SEASON TYPES: {season_types}')
        
        return True
    
    with DATABASE:
        index_reached = repeater(
            _collect_data,
            starting_index,
            wait_interval
        )

    return index_reached

# Query
def get_all_team_game_data() -> pd.DataFrame:
    with DATABASE:
        data = DATABASE.query_dataframe()

    return data

# TODO: Add an optional season parameter
def get_team_game_data(team_id: str) -> pd.DataFrame:
    SQL_condition = f"{TEAM_ID.category_name} = :{TEAM_ID.category_name}"
    condition_params = {TEAM_ID : team_id}

    with DATABASE:
        data = DATABASE.query_dataframe(
            SQL_condition=SQL_condition, 
            condition_params=condition_params
        )

    return data