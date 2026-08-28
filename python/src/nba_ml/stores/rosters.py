"""
Who is on each team right now, and who is hurt.

Every other store holds what happened. This one holds what is about to: the team a data service
currently has each player on, and the word its injury report uses about them. That is what turns the
site's roster controls from an empty form into who is actually expected to take the floor.

It is a snapshot rather than a history. Each collection replaces the whole table, because a player
who has left a roster has to leave this one too, and a row nobody rewrote would go on naming a team
they no longer play for. When the table is empty nothing is assumed, which is exactly how every
prediction behaved before this store existed.
"""

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
"""The injury report's own word, or null for a player it says nothing about."""

COLLECTED_AT = ALL_CATEGORIES.add_category("COLLECTED_AT", DataType.TEXT)
"""When the snapshot was taken, in UTC. The same value on every row of one collection."""

# Database
FILEPATH = paths.database_file("rosters")
NAME = "rosters"
PRIMARY_KEYS = [
    PLAYER_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

# A roster is almost always read one team at a time, and the primary key is the player.
INDEXES = [
    [TEAM_ID]
]

DATABASE = Database(
    FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS, INDEXES
)

READ_CATEGORIES = [PLAYER_ID, TEAM_ID, STATUS]
"""The order _from_row reads a row in, named outright so a column added later cannot shift it."""

def _from_row(row: tuple) -> RosterEntry:
    player_id, team_id, status = row

    return RosterEntry(int(player_id), int(team_id), status)

# Writing
def store(entries: Collection[RosterEntry]) -> int:
    """
    Replaces the whole snapshot with the given one and returns how many rows were written.

    An empty snapshot is refused rather than written, because a service that answered with nothing
    and a league with nobody on it are the same table, and only one of them is real.
    """

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
    """Who a data service currently has on one team, hurt or not."""

    return _entries(
        f"{TEAM_ID.category_name} = :{TEAM_ID.category_name}",
        {TEAM_ID : team_id}
    )

def entries_for(player_ids: Collection[int]) -> dict[int, RosterEntry]:
    """
    What the snapshot says about the named players, keyed by player.

    A player it says nothing about is simply absent from the answer, which is how a caller tells "no
    longer on this team" apart from "this service has never heard of them".
    """

    if not player_ids:
        return {}

    found = _entries(held_in(PLAYER_ID, player_ids))

    return {entry.player_id: entry for entry in found}

def collected_at() -> datetime | None:
    """When the held snapshot was taken, or None while none has been. Says how stale it is."""

    with DATABASE:
        newest = DATABASE.max_value(COLLECTED_AT)

    return None if newest is None else datetime.fromisoformat(newest)
