"""Season types, season years and date helpers."""

from datetime import date, datetime
from enum import Enum
from zoneinfo import ZoneInfo

class SeasonType(Enum):
    """The parts of an NBA season."""

    PRESEASON = "PRESEASON"
    REGULAR_SEASON = "REGULAR_SEASON"
    PLAYOFFS = "PLAYOFFS"
    PLAY_IN = "PLAY_IN"

# Month a season starts. A season is identified by the year it starts in.
SEASON_START_MONTH = 10

PLAYER_GAME_COLLECTION_START_DATE = date(2019, 10, 22)
"""First date the data source has box scores with every stat the player models need."""

COLLECTION_START_SEASON = PLAYER_GAME_COLLECTION_START_DATE.year
"""First season collected from the data source."""

ARCHIVE_START_SEASON = 1996
"""Oldest season with player box scores on nba.com."""

TRAINING_START_SEASONS = (ARCHIVE_START_SEASON, COLLECTION_START_SEASON)
"""Start seasons the training command can choose between."""

def season_of(day: date) -> int:
    """Returns the season a date belongs to, as the year that season started."""

    return day.year if day.month >= SEASON_START_MONTH else day.year - 1

def season_start_date(season_year: int) -> datetime:
    return datetime(season_year, SEASON_START_MONTH, 1)

EASTERN_TIMEZONE = ZoneInfo("America/New_York")
"""Game dates are US Eastern dates."""

def today() -> date:
    """Returns today's date in US Eastern time."""

    return datetime.now(EASTERN_TIMEZONE).date()

def current_season() -> int:
    return season_of(today())

# The first digit of a game ID tells its season type.
GAME_ID_PREFIXES = {
    SeasonType.PRESEASON: "1",
    SeasonType.REGULAR_SEASON: "2",
    SeasonType.PLAYOFFS: "4",
    SeasonType.PLAY_IN: "5"
}

def season_type_of_game_id(game_id: int) -> SeasonType | None:
    """Returns the season type of a game ID, or None if its prefix is not recognized."""

    prefix = str(game_id)[0]

    return next(
        (season_type for season_type, value in GAME_ID_PREFIXES.items() if value == prefix),
        None
    )

DATE_FORMAT = "%Y-%m-%d"

def to_date_string(day: date) -> str:
    return day.strftime(DATE_FORMAT)

def from_date_string(text: str) -> datetime:
    return datetime.strptime(text, DATE_FORMAT)
