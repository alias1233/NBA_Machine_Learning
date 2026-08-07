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

# A season is named after the year it starts in, and the next one starts in October. This is the
# only place that boundary is decided. game_columns.season_of applies the same rule to a column.
SEASON_START_MONTH = 10

def season_of(day: date) -> int:
    """The season a date falls in, named after the year that season started."""

    return day.year if day.month >= SEASON_START_MONTH else day.year - 1

def current_season() -> int:
    return season_of(datetime.now())

# A game id such as "0022300001" writes its season phase in the third character. Ids are stored as
# numbers, so the two leading zeros are gone and it is the first one. This is the only place that
# mapping is decided, and both the feature columns and the schedule read it.
GAME_ID_PREFIXES = {
    SeasonType.PRESEASON: "1",
    SeasonType.REGULAR_SEASON: "2",
    SeasonType.PLAYOFFS: "4",
    SeasonType.PLAY_IN: "5"
}

def season_type_of_game_id(game_id: int) -> SeasonType | None:
    """
    The phase a game id belongs to, or None for a phase this project does not model. The All-Star
    game is the one of those that appears on a schedule, and it never appears in a box score.
    """

    prefix = str(game_id)[0]

    return next(
        (season_type for season_type, value in GAME_ID_PREFIXES.items() if value == prefix),
        None
    )

DATE_FORMAT = "%Y-%m-%d"

def to_date_string(day: date) -> str:
    """Game dates are held as text, so a date has to be written the same way everywhere."""

    return day.strftime(DATE_FORMAT)

def from_date_string(text: str) -> datetime:
    return datetime.strptime(text, DATE_FORMAT)
