"""Stores player info such as name, height, weight and draft number."""

from typing import Iterable

import pandas as pd

from nba_ml import paths
from nba_ml.database import Categories, Database, DataConflictHandler, DataType
from nba_ml.entities import Player
from nba_ml.stores import searchable

# Categories
ALL_CATEGORIES = Categories()
PLAYER_ID = ALL_CATEGORIES.add_category("PERSON_ID", DataType.INTEGER)
PLAYER_NAME = ALL_CATEGORIES.add_category("PLAYER_NAME", DataType.TEXT)
HEIGHT = ALL_CATEGORIES.add_category("HEIGHT", DataType.INTEGER)
WEIGHT = ALL_CATEGORIES.add_category("WEIGHT", DataType.REAL)
POSITION = ALL_CATEGORIES.add_category("POSITION", DataType.TEXT)
FROM_YEAR = ALL_CATEGORIES.add_category("FROM_YEAR", DataType.INTEGER)
TO_YEAR = ALL_CATEGORIES.add_category("TO_YEAR", DataType.INTEGER)
BIRTHDATE = ALL_CATEGORIES.add_category("BIRTHDATE", DataType.TEXT)
DRAFT_NUMBER = ALL_CATEGORIES.add_category("DRAFT_NUMBER", DataType.INTEGER)

# Database
FILEPATH = paths.database_file("player_info")
NAME = "player_info"
PRIMARY_KEYS = [
    PLAYER_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

DATABASE = Database(FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# Writing
def store(player_info: pd.DataFrame) -> int:
    """Inserts the given rows, replacing existing players. Returns the number of rows written."""

    if PLAYER_NAME.category_name not in player_info.columns:
        player_info = player_info.assign(**{PLAYER_NAME.category_name: None})

    with DATABASE:
        return DATABASE.add_dataframe(player_info)

# Query
def get_all_players_info() -> pd.DataFrame:
    with DATABASE:
        data = DATABASE.query_dataframe()

    return data

def stored_player_ids() -> set[int]:
    """Returns the IDs of every stored player."""

    with DATABASE:
        rows = DATABASE.query(categories=[PLAYER_ID])

    return {int(row[0]) for row in rows}

def _named_players(
    SQL_condition: str | None = None,
    condition_params: dict | None = None
    ) -> list[Player]:
    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=SQL_condition,
            condition_params=condition_params,
            categories=[PLAYER_ID, PLAYER_NAME]
        )

    return [Player(int(player_id), name) for player_id, name in rows if name is not None]

def get_players(player_ids: Iterable[int]) -> list[Player]:
    """Returns the given players that have a name, in the order the IDs were given."""

    named = {player.id: player for player in _named_players()}

    return [named[player_id] for player_id in player_ids if player_id in named]

def get_player(player_id: int) -> Player | None:
    found = _named_players(
        f"{PLAYER_ID.category_name} = :{PLAYER_ID.category_name}",
        {PLAYER_ID : player_id}
    )

    return found[0] if found else None

def find_by_name(text: str, limit: int | None = None) -> list[Player]:
    """Returns players whose name contains the text. Names starting with it come first."""

    wanted = searchable(text)
    found = [player for player in _named_players() if wanted in searchable(player.name)]
    found.sort(key=lambda player: (not searchable(player.name).startswith(wanted), player.name))

    return found if limit is None else found[:limit]

def player_ids_without_names() -> list[int]:
    """Returns the IDs of stored players with no name."""

    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=f"{PLAYER_NAME.category_name} IS NULL",
            categories=[PLAYER_ID]
        )

    return [int(row[0]) for row in rows]
