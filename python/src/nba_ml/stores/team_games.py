"""One row per team per finished game, straight off the box score."""

from datetime import date, datetime

import pandas as pd

from nba_ml import paths, season
from nba_ml.database import Categories, Database, DataConflictHandler, DataType

# Categories
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
FILEPATH = paths.database_file("team_game_data")
NAME = "teams"
PRIMARY_KEYS = [
    TEAM_ID,
    GAME_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

DATABASE = Database(FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Writing
def store(team_game_data: pd.DataFrame) -> int:
    """Adds the given rows, replacing any game already held. Returns how many were written."""

    with DATABASE:
        return DATABASE.add_dataframe(team_game_data)

# Query
def get_all_team_game_data() -> pd.DataFrame:
    with DATABASE:
        data = DATABASE.query_dataframe()

    return data

def get_game_data_after_date(date_start: datetime) -> pd.DataFrame:
    SQL_condtition = f"{GAME_DATE.category_name} >= :{GAME_DATE.category_name}"
    condition_params = {GAME_DATE : season.to_date_string(date_start)}

    with DATABASE:
        data = DATABASE.query_dataframe(
            SQL_condition=SQL_condtition,
            condition_params=condition_params
        )

    return data

def latest_game_date() -> date | None:
    """The newest game held, which is where an update run starts from. None when nothing is held."""

    with DATABASE:
        newest = DATABASE.max_value(GAME_DATE)

    return None if newest is None else season.from_date_string(newest).date()
