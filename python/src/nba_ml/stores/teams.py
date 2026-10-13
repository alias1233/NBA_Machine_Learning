"""Stores the NBA teams."""

import pandas as pd

from nba_ml import paths
from nba_ml.database import Categories, Database, DataConflictHandler, DataType
from nba_ml.entities import Team
from nba_ml.stores import searchable

# Categories
ALL_CATEGORIES = Categories()
TEAM_ID = ALL_CATEGORIES.add_category("TEAM_ID", DataType.INTEGER)
ABBREVIATION = ALL_CATEGORIES.add_category("ABBREVIATION", DataType.TEXT)
TEAM_NAME = ALL_CATEGORIES.add_category("TEAM_NAME", DataType.TEXT)

# Database
FILEPATH = paths.database_file("teams")
NAME = "teams"
PRIMARY_KEYS = [
    TEAM_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

DATABASE = Database(FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Writing
def store(teams: pd.DataFrame) -> int:
    """Inserts the given rows, replacing existing teams. Returns the number of rows written."""

    with DATABASE:
        return DATABASE.add_dataframe(teams)

# Query
def all_teams() -> list[Team]:
    with DATABASE:
        rows = DATABASE.query(categories=[TEAM_ID, TEAM_NAME, ABBREVIATION])

    return [Team(int(team_id), name, abbreviation) for team_id, name, abbreviation in rows]

def find(abbreviation_or_name: str) -> Team | None:
    """Returns the team matching an abbreviation or part of a team name, or None."""

    text = searchable(abbreviation_or_name)

    for team in all_teams():
        if text == searchable(team.abbreviation) or text in searchable(team.name):
            return team

    return None
