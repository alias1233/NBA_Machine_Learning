"""
The vocabulary of an NBA season: its phases, its years, and how a game date is written.

Nothing here knows where data comes from or where it is stored, so every stage can use it and a
change of data source cannot reach it.
"""

from datetime import date, datetime
from enum import Enum

class SeasonType(Enum):
    """
    The phases a season is played in. The values are the names the feature columns carry, so a
    season type crosses the whole pipeline without a translation table.
    """

    PRESEASON = "PRESEASON"
    REGULAR_SEASON = "REGULAR_SEASON"
    PLAYOFFS = "PLAYOFFS"
    PLAY_IN = "PLAY_IN"

# A season is named after the year it starts in, and the next one starts in October.
SEASON_START_MONTH = 10

def season_of(day: date) -> int:
    """The season a date falls in, named after the year that season started."""

    return day.year if day.month >= SEASON_START_MONTH else day.year - 1

def current_season() -> int:
    return season_of(datetime.now())

DATE_FORMAT = "%Y-%m-%d"

def to_date_string(day: date) -> str:
    """Game dates are held as text, so a date has to be written the same way everywhere."""

    return day.strftime(DATE_FORMAT)

def from_date_string(text: str) -> datetime:
    return datetime.strptime(text, DATE_FORMAT)
