"""One row per player per finished game, straight off the box score."""

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

# A date narrows almost every read here, and a roster read names a team and its games. The primary
# key covers neither, so without these the whole archive is scanned each time.
INDEXES = [
    [GAME_DATE],
    [TEAM_ID, GAME_ID]
]

DATABASE = Database(
    FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS, INDEXES
)

# Writing
def store(player_game_data: pd.DataFrame) -> int:
    """Adds the given rows, replacing any game already held. Returns how many were written."""

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
    """
    Every stored game of the named players, which is what a prediction reads around one player: the
    player themselves and the team mates whose recent form its roster columns total.
    """

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
    """Who played for a team in the named games, which is the roster around those games."""

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
    """
    What each of the named players was averaging in minutes over their last few games before a date.

    Minutes stand in for how much of a team a player is, so this is what says whether somebody
    joining a roster is worth counting. Only the players with a stored game before the date appear.

    Args:
        games is how many of each player's own most recent games the average is taken over.
    """

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
    """The newest game held, which is where an update run starts from. None when nothing is held."""

    with DATABASE:
        newest = DATABASE.max_value(GAME_DATE)

    return None if newest is None else season.from_date_string(newest).date()

def oldest_game_date_outside(game_ids: Collection[int]) -> date | None:
    """
    The date of the oldest game held here that is not among the given ones, or None when every one
    of them is.

    A team row is a total of these rows, so this is what says how far back a rebuild of the team
    store has to reach to leave no stored game without one. See data_collection/games.py.
    """

    held = {int(game_id) for game_id in game_ids}

    with DATABASE:
        rows = DATABASE.cursor.execute(
            f"SELECT {GAME_ID.category_name}, MIN({GAME_DATE.category_name}) "
            f"FROM {NAME} GROUP BY {GAME_ID.category_name}"
        ).fetchall()

    outside = [game_date for game_id, game_date in rows if int(game_id) not in held]

    return season.from_date_string(min(outside)).date() if outside else None

def latest_team_id(player_id: int, before: date | None = None) -> int | None:
    """
    The team a player last played for, which is the team they are on unless they have just moved.
    None when they have no recorded game.
    """

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
    """
    Who a team's players are, taken as everyone whose most recent game since the given date was
    for that team. A traded player therefore lands on the team they last played for.
    """

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
    """Who has played since the given date, which is who is worth refreshing information for."""

    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=f"{GAME_DATE.category_name} >= :{GAME_DATE.category_name}",
            condition_params={GAME_DATE : season.to_date_string(date_start)},
            categories=[PLAYER_ID],
            distinct=True
        )

    return sorted(int(row[0]) for row in rows)

def career_seasons() -> dict[int, tuple[int, int]]:
    """The first and last season each stored player appeared in."""

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
