"""
Every game of a season, played or not.

This is the only table holding games that have no box score, and it is what lets the site name a
game before it happens. The whole season is kept rather than only what is still to come, because
deciding whether an upcoming game can be predicted means knowing which earlier games are still
missing. See nba_ml/upcoming.py for that rule.

A mock game is one added by hand for testing. It is stored beside the real ones so it behaves
exactly like one, and it carries a flag so every mock game can be removed in a single step.
"""

from datetime import date, datetime

import pandas as pd

from nba_ml import paths, season
from nba_ml.database import Categories, Database, DataConflictHandler, DataType
from nba_ml.entities import Game, GameStatus, ScheduledGame

# Categories
ALL_CATEGORIES = Categories()
GAME_ID = ALL_CATEGORIES.add_category("GAME_ID", DataType.INTEGER)
GAME_DATE = ALL_CATEGORIES.add_category("GAME_DATE", DataType.TEXT)
TIPOFF = ALL_CATEGORIES.add_category("TIPOFF", DataType.TEXT)
"""When the game starts, written in UTC. Null when the service does not publish a time yet."""

HOME_TEAM_ID = ALL_CATEGORIES.add_category("HOME_TEAM_ID", DataType.INTEGER)
AWAY_TEAM_ID = ALL_CATEGORIES.add_category("AWAY_TEAM_ID", DataType.INTEGER)
SEASON_TYPE = ALL_CATEGORIES.add_category("SEASON_TYPE", DataType.TEXT)
STATUS = ALL_CATEGORIES.add_category("STATUS", DataType.TEXT)
IS_MOCK = ALL_CATEGORIES.add_category("IS_MOCK", DataType.INTEGER)

# Database
FILEPATH = paths.database_file("schedule")
NAME = "games"
PRIMARY_KEYS = [
    GAME_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.REPLACE

DATABASE = Database(FILEPATH, NAME, ALL_CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)

# A mock game's id keeps the shape of a real one, phase digit first, with a season of 99 that no real
# season produces. That is only so the two cannot collide. IS_MOCK is what removal reads.
MOCK_SEASON_DIGITS = "99"

def _to_row(game: ScheduledGame) -> dict:
    return {
        GAME_ID.category_name : game.id,
        GAME_DATE.category_name : season.to_date_string(game.game.date),
        TIPOFF.category_name : None if game.tipoff is None else game.tipoff.isoformat(),
        HOME_TEAM_ID.category_name : game.game.home_team_id,
        AWAY_TEAM_ID.category_name : game.game.away_team_id,
        SEASON_TYPE.category_name : game.game.season_type.value,
        STATUS.category_name : game.status.value,
        IS_MOCK.category_name : int(game.is_mock)
    }

READ_CATEGORIES = [
    GAME_ID,
    GAME_DATE,
    TIPOFF,
    HOME_TEAM_ID,
    AWAY_TEAM_ID,
    SEASON_TYPE,
    STATUS,
    IS_MOCK
]
"""The order _from_row reads a row in, named outright so a column added later cannot shift it."""

def _from_row(row: tuple) -> ScheduledGame:
    game_id, game_date, tipoff, home_team_id, away_team_id, season_type, status, is_mock = row

    return ScheduledGame(
        id=int(game_id),
        game=Game(
            season.from_date_string(game_date).date(),
            int(home_team_id),
            int(away_team_id),
            season.SeasonType(season_type)
        ),
        status=GameStatus(status),
        tipoff=None if tipoff is None else datetime.fromisoformat(tipoff),
        is_mock=bool(is_mock)
    )

# Writing
def store(games: list[ScheduledGame]) -> int:
    """Adds the given games, replacing any already held. Returns how many were written."""

    if not games:
        return 0

    with DATABASE:
        return DATABASE.add_dataframe(pd.DataFrame([_to_row(game) for game in games]))

def next_mock_game_id(season_type: season.SeasonType) -> int:
    """An unused id for a mock game of the given phase, following on from the mock games held."""

    prefix = season.GAME_ID_PREFIXES[season_type] + MOCK_SEASON_DIGITS
    held = [game.id for game in all_mock_games() if str(game.id).startswith(prefix)]

    return max(held) + 1 if held else int(prefix + "00001")

# Query
def _games(
    SQL_condition: str | None = None,
    condition_params: dict | None = None
    ) -> list[ScheduledGame]:
    with DATABASE:
        rows = DATABASE.query(
            SQL_condition=SQL_condition,
            condition_params=condition_params,
            categories=READ_CATEGORIES,
            order_by=f"{GAME_DATE.category_name}, {TIPOFF.category_name}"
        )

    return [_from_row(row) for row in rows]

def all_games() -> list[ScheduledGame]:
    return _games()

def all_mock_games() -> list[ScheduledGame]:
    return _games(f"{IS_MOCK.category_name} = 1")

def games_on_or_after(day: date) -> list[ScheduledGame]:
    return _games(
        f"{GAME_DATE.category_name} >= :{GAME_DATE.category_name}",
        {GAME_DATE : season.to_date_string(day)}
    )

def get_game(game_id: int) -> ScheduledGame | None:
    found = _games(
        f"{GAME_ID.category_name} = :{GAME_ID.category_name}",
        {GAME_ID : game_id}
    )

    return found[0] if found else None

def remove_mock_games() -> int:
    """Deletes every mock game and returns how many went. Real games are untouched."""

    with DATABASE:
        return DATABASE.delete(f"{IS_MOCK.category_name} = 1")
