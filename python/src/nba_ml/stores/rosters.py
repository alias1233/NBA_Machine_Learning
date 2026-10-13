"""Stores the latest roster and injury snapshot."""

from datetime import datetime, timezone
from typing import Collection

import pandas as pd

from nba_ml import paths
from nba_ml.database import Categories, Database, DataConflictHandler, DataType, held_in
from nba_ml.entities import RosterEntry

# Categories
ALL_CATEGORIES = Categories()
PLAYER_ID = ALL_CATEGORIES.add_category("PLAYER_ID", DataType.INTEGER)
TEAM_ID = ALL_CATEGORIES.add_category("TEAM_ID", DataType.INTEGER)
STATUS = ALL_CATEGORIES.add_category("STATUS", DataType.TEXT)
"""Injury status from the injury report, or null if the player is not on it."""

COLLECTED_AT = ALL_CATEGORIES.add_category("COLLECTED_AT", DataType.TEXT)
"""Time the snapshot was collected, in UTC."""

# Database
FILEPATH = paths.database_file("rosters")
NAME = "rosters"
PRIMARY_KEYS = [
    PLAYER_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

INDEXES = [
    [TEAM_ID]
]

DATABASE = Database(
    FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS, INDEXES
)

READ_CATEGORIES = [PLAYER_ID, TEAM_ID, STATUS]
"""Column order expected by _from_row."""

def _from_row(row: tuple) -> RosterEntry:
    player_id, team_id, status = row

    return RosterEntry(int(player_id), int(team_id), status)

# Writing
def store(entries: Collection[RosterEntry]) -> int:
    """Replaces the stored snapshot with the given entries. Returns the number of rows written."""

    if not entries:
        raise ValueError("A roster snapshot cannot be empty. Nothing was stored.")

    collected_at = datetime.now(timezone.utc).isoformat()

    with DATABASE:
        DATABASE.delete(f"{PLAYER_ID.category_name} IS NOT NULL")

        return DATABASE.add_dataframe(pd.DataFrame([
            {
                PLAYER_ID.category_name: entry.player_id,
                TEAM_ID.category_name: entry.team_id,
                STATUS.category_name: entry.status,
                COLLECTED_AT.category_name: collected_at
            }
            for entry in entries
        ]))

# Query
def _entries(
    SQL_condition: str | None = None,
    condition_params: dict | None = None
    ) -> list[RosterEntry]:
    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=SQL_condition,
            condition_params=condition_params,
            categories=READ_CATEGORIES
        )

    return [_from_row(row) for row in rows]

def on_team(team_id: int) -> list[RosterEntry]:
    """Returns the roster entries for the given team."""

    return _entries(
        f"{TEAM_ID.category_name} = :{TEAM_ID.category_name}",
        {TEAM_ID : team_id}
    )

def entries_for(player_ids: Collection[int]) -> dict[int, RosterEntry]:
    """Returns the roster entries for the given players, keyed by player ID."""

    if not player_ids:
        return {}

    found = _entries(held_in(PLAYER_ID, player_ids))

    return {entry.player_id: entry for entry in found}

def collected_at() -> datetime | None:
    """Returns when the stored snapshot was collected, or None if there isn't one."""

    with DATABASE:
        newest = DATABASE.max_value(COLLECTED_AT)

    return None if newest is None else datetime.fromisoformat(newest)
