"""
A player's own information, the part that does not change from game to game.

The name is held here as well as the modelled columns, because it is what a person types and what a
page displays, and neither should need a data service to answer.
"""

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
    """
    Adds the given rows, replacing any player already held. Returns how many were written.

    The name is the one column a row may arrive without. Not every service carries it alongside a
    player's other information, so collection fills it in from the service's player list instead.
    """

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
    """Which players are already held, so a collection run can skip them."""

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
    """The named players among the given ids, in the order they were given."""

    named = {player.id: player for player in _named_players()}

    return [named[player_id] for player_id in player_ids if player_id in named]

def get_player(player_id: int) -> Player | None:
    found = _named_players(
        f"{PLAYER_ID.category_name} = :{PLAYER_ID.category_name}",
        {PLAYER_ID : player_id}
    )

    return found[0] if found else None

def find_by_name(text: str, limit: int | None = None) -> list[Player]:
    """
    Every held player whose name contains the given text, the ones it starts first.

    Matching is done here rather than in SQL because it ignores accents, which SQL's LIKE does not.
    """

    wanted = searchable(text)
    found = [player for player in _named_players() if wanted in searchable(player.name)]
    found.sort(key=lambda player: (not searchable(player.name).startswith(wanted), player.name))

    return found if limit is None else found[:limit]

def player_ids_without_names() -> list[int]:
    """Players whose row arrived without a name, which a collection run fills in."""

    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=f"{PLAYER_NAME.category_name} IS NULL",
            categories=[PLAYER_ID]
        )

    return [int(row[0]) for row in rows]
