"""Stores player box scores, one row per player per game."""

from datetime import date
from typing import Collection

import pandas as pd

from nba_ml import paths, season
from nba_ml.database import Categories, Database, DataConflictHandler, DataType, held_in

# Categories
ALL_CATEGORIES = Categories()
PLAYER_ID = ALL_CATEGORIES.add_category("PLAYER_ID", DataType.INTEGER)
GAME_ID = ALL_CATEGORIES.add_category("GAME_ID", DataType.INTEGER)
TEAM_ID = ALL_CATEGORIES.add_category("TEAM_ID", DataType.INTEGER)
GAME_DATE = ALL_CATEGORIES.add_category("GAME_DATE", DataType.TEXT)
SEASON_TYPE = ALL_CATEGORIES.add_category("SEASON_TYPE", DataType.TEXT)
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
PLUS_MINUS = ALL_CATEGORIES.add_category("PLUS_MINUS", DataType.INTEGER)

# Database
FILEPATH = paths.database_file("player_game_data")
NAME = "players"
PRIMARY_KEYS = [
    PLAYER_ID,
    GAME_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

INDEXES = [
    [GAME_DATE],
    [TEAM_ID, GAME_ID]
]

DATABASE = Database(
    FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS, INDEXES
)

# Writing
def store(player_game_data: pd.DataFrame) -> int:
    """Inserts the given rows, replacing existing ones. Returns the number of rows written."""

    with DATABASE:
        return DATABASE.add_dataframe(player_game_data)

# Query
def get_all_player_game_data() -> pd.DataFrame:
    with DATABASE:
        data = DATABASE.query_dataframe()

    return data

def get_specific_player_game_data(
        player_id: int,
        date_start: date | None = None
        ) -> pd.DataFrame:
    SQL_condition = f"{PLAYER_ID.category_name} = :{PLAYER_ID.category_name}"
    condition_params: dict = {PLAYER_ID : player_id}

    if date_start is not None:
        SQL_condition += f" AND {GAME_DATE.category_name} >= :{GAME_DATE.category_name}"
        condition_params[GAME_DATE] = season.to_date_string(date_start)
    with DATABASE:
        data = DATABASE.query_dataframe(
            SQL_condition=SQL_condition,
            condition_params=condition_params
        )

    return data

def get_players_game_data(
        player_ids: Collection[int],
        date_start: date | None = None
        ) -> pd.DataFrame:
    """Returns every stored game for the given players, optionally from date_start onwards."""

    if not player_ids:
        return pd.DataFrame(columns=DATABASE.category_names)

    SQL_condition = held_in(PLAYER_ID, player_ids)
    condition_params: dict = {}

    if date_start is not None:
        SQL_condition += f" AND {GAME_DATE.category_name} >= :{GAME_DATE.category_name}"
        condition_params[GAME_DATE] = season.to_date_string(date_start)

    with DATABASE:
        data = DATABASE.query_dataframe(
            SQL_condition=SQL_condition,
            condition_params=condition_params or None
        )

    return data

def player_ids_in_games(team_id: int, game_ids: Collection[int]) -> set[int]:
    """Returns the IDs of players who played for the team in the given games."""

    if not game_ids:
        return set()

    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=(
                f"{TEAM_ID.category_name} = :{TEAM_ID.category_name} AND {held_in(GAME_ID, game_ids)}"
            ),
            condition_params={TEAM_ID : team_id},
            categories=[PLAYER_ID],
            distinct=True
        )

    return {int(row[0]) for row in rows}

def recent_mean_minutes(
    player_ids: Collection[int],
    before: date,
    games: int
    ) -> dict[int, float]:
    """Returns each player's average minutes over their last `games` games before the given date."""

    if not player_ids:
        return {}

    with DATABASE:
        rows = DATABASE.cursor.execute(
            f"SELECT {PLAYER_ID.category_name}, AVG({MINUTES_PLAYED.category_name}) FROM ("
            f"SELECT {PLAYER_ID.category_name}, {MINUTES_PLAYED.category_name}, ROW_NUMBER() OVER ("
            f"PARTITION BY {PLAYER_ID.category_name} ORDER BY {GAME_DATE.category_name} DESC"
            f") AS PLAYED_AGO FROM {NAME} "
            f"WHERE {held_in(PLAYER_ID, player_ids)} "
            f"AND {GAME_DATE.category_name} < :{GAME_DATE.category_name}"
            f") WHERE PLAYED_AGO <= :GAMES GROUP BY {PLAYER_ID.category_name}",
            {GAME_DATE.category_name : season.to_date_string(before), "GAMES" : int(games)}
        ).fetchall()

    return {int(player_id): float(minutes) for player_id, minutes in rows if minutes is not None}

def get_game_data_after_date(date_start: date) -> pd.DataFrame:
    with DATABASE:
        data = DATABASE.query_dataframe(
            SQL_condition=f"{GAME_DATE.category_name} >= :{GAME_DATE.category_name}",
            condition_params={GAME_DATE : season.to_date_string(date_start)}
        )

    return data

def latest_game_date() -> date | None:
    """Returns the date of the latest stored game, or None if the store is empty."""

    with DATABASE:
        newest = DATABASE.max_value(GAME_DATE)

    return None if newest is None else season.from_date_string(newest).date()

def oldest_game_date_outside(game_ids: Collection[int]) -> date | None:
    """Returns the date of the oldest stored game not in game_ids, or None if there isn't one."""

    held = {int(game_id) for game_id in game_ids}

    with DATABASE:
        rows = DATABASE.cursor.execute(
            f"SELECT {GAME_ID.category_name}, MIN({GAME_DATE.category_name}) "
            f"FROM {NAME} GROUP BY {GAME_ID.category_name}"
        ).fetchall()

    outside = [game_date for game_id, game_date in rows if int(game_id) not in held]

    return season.from_date_string(min(outside)).date() if outside else None

def latest_team_id(player_id: int, before: date | None = None) -> int | None:
    """Returns the ID of the team the player last played for, or None if they have no stored games."""

    SQL_condition = f"{PLAYER_ID.category_name} = :{PLAYER_ID.category_name}"
    condition_params: dict = {PLAYER_ID : player_id}

    if before is not None:
        SQL_condition += f" AND {GAME_DATE.category_name} < :{GAME_DATE.category_name}"
        condition_params[GAME_DATE] = season.to_date_string(before)

    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=SQL_condition,
            condition_params=condition_params,
            categories=[TEAM_ID],
            limit=1,
            order_by=f"{GAME_DATE.category_name} DESC"
        )

    return None if not rows else int(rows[0][0])

def player_ids_on_team(team_id: int, date_start: date) -> list[int]:
    """Returns the players whose most recent game since date_start was for the given team."""

    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=f"{GAME_DATE.category_name} >= :{GAME_DATE.category_name}",
            condition_params={GAME_DATE : season.to_date_string(date_start)},
            categories=[PLAYER_ID, TEAM_ID, GAME_DATE]
        )

    latest: dict[int, tuple[str, int]] = {}
    for player_id, played_for, game_date in rows:
        player_id = int(player_id)
        if game_date >= latest.get(player_id, ("", 0))[0]:
            latest[player_id] = (game_date, int(played_for))

    return sorted(player_id for player_id, (_, played_for) in latest.items() if played_for == team_id)

def player_ids_since(date_start: date) -> list[int]:
    """Returns the IDs of players with a game on or after the given date."""

    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=f"{GAME_DATE.category_name} >= :{GAME_DATE.category_name}",
            condition_params={GAME_DATE : season.to_date_string(date_start)},
            categories=[PLAYER_ID],
            distinct=True
        )

    return sorted(int(row[0]) for row in rows)

def career_seasons() -> dict[int, tuple[int, int]]:
    """Returns each player's first and last season, based on their stored games."""

    with DATABASE:
        rows = DATABASE.cursor.execute(
            f"SELECT {PLAYER_ID.category_name}, MIN({GAME_DATE.category_name}), "
            f"MAX({GAME_DATE.category_name}) FROM {NAME} GROUP BY {PLAYER_ID.category_name}"
        ).fetchall()

    return {
        int(player_id): (
            season.season_of(season.from_date_string(first_game).date()),
            season.season_of(season.from_date_string(last_game).date())
        )
        for player_id, first_game, last_game in rows
    }
