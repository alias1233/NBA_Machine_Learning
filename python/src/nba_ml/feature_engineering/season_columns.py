"""
Where a game sits in its season: which phase it belongs to, how far into the season it is, and how
the team's season is going up to it.

The season a date falls in is decided once, in nba_ml/season.py. This applies that same rule to a
whole column and builds the columns a model reads it through.
"""

import pandas as pd

from nba_ml.feature_engineering.game_columns import BUILT_COLUMN_TYPE, encode_equality_as_integer
from nba_ml.season import GAME_ID_PREFIXES, SEASON_START_MONTH, SeasonType

def season_of(game_dates: pd.Series) -> pd.Series:
    """
    The calendar year each game's season started in, which is season.season_of over a whole column.
    The dates must be in datetime form.
    """

    return game_dates.dt.year - (game_dates.dt.month < SEASON_START_MONTH)

### SEASON TYPES: A value of 1 represents True, and a value of 0 represents False. ###
# One name per season phase, taken from the shared enum so a prediction can name the phase of the
# game it is asking about without a translation table.
PRESEASON = SeasonType.PRESEASON.value
REGULAR_SEASON = SeasonType.REGULAR_SEASON.value
PLAYOFFS = SeasonType.PLAYOFFS.value
PLAY_IN = SeasonType.PLAY_IN.value
ALL_SEASON_TYPES = [
    PRESEASON,
    REGULAR_SEASON,
    PLAYOFFS,
    PLAY_IN
]
SEASON_ENCODINGS = {
    season_type.value : prefix
    for season_type, prefix in GAME_ID_PREFIXES.items()
}
SEASON_TYPE = 'SEASON_TYPE'
"""
Which phase a game belongs to, as the one character a game id names it with.

A label rather than a model input: the columns above are what a model reads, and this is what
grouping a subject's games by phase needs.
"""

def drop_incomplete_game_rows(
    game_data: pd.DataFrame,
    stored_season_type_column: str,
    optional_columns: tuple[str, ...] = ()
    ) -> pd.DataFrame:
    """Drops incomplete rows while keeping legacy rows whose season phase can be inferred."""

    optional = {stored_season_type_column, *optional_columns}
    required = [column for column in game_data.columns if column not in optional]
    return game_data.dropna(subset=required)

def add_encoded_season_type_columns(
    team_game_data: pd.DataFrame,
    game_id_column: str,
    season_type_column: str | None = None
    ) -> pd.DataFrame:
    """
    The season type is the third character of a game id such as "0022300001". Reading the first
    character works only because the id is stored as a number, which drops the two leading zeros.
    Storing game ids as text would silently break this.
    """

    inferred = team_game_data[game_id_column].astype(str).str[0]
    season_type_id = (
        inferred if season_type_column is None
        else team_game_data[season_type_column].fillna(inferred).astype(str)
    )
    team_game_data[SEASON_TYPE] = season_type_id

    for season_type in ALL_SEASON_TYPES:
        team_game_data[season_type] = encode_equality_as_integer(season_type_id, SEASON_ENCODINGS[season_type])

    return team_game_data

SEASON_GAME_NUMBER = 'SEASON_GAME_NUMBER'
DAYS_INTO_SEASON = 'DAYS_INTO_SEASON'
TEAM_WIN_PERCENTAGE = 'TEAM_WIN_PERCENTAGE'
ALL_SEASON_CONTEXT_COLUMNS = [SEASON_GAME_NUMBER, DAYS_INTO_SEASON, TEAM_WIN_PERCENTAGE]
EVEN_RECORD = 0.5
def add_season_standings_columns(
    team_game_data: pd.DataFrame,
    game_date_column: str,
    team_id_column: str,
    won_column: str,
    regular_season_column: str
    ) -> pd.DataFrame:
    """
    Adds how far into its season each team game sits and how the team's season is going.

    SEASON_GAME_NUMBER and DAYS_INTO_SEASON place the game in the season. TEAM_WIN_PERCENTAGE says
    how much the game is still worth to the team, which separates a contender resting a star from an
    eliminated team handing minutes to its bench.

    Only regular season games count towards the record, and a game never counts itself. A playoff
    game therefore reads the record the team finished the regular season on, and a preseason game
    reads an even one.

    The given team_game_data must be sorted by game date, grouped by team id, with the date column
    in datetime form and the won column already encoded as 1 for a win.
    """

    game_dates = team_game_data[game_date_column]
    team_and_season = [team_game_data[team_id_column], season_of(game_dates)]
    played = team_game_data[regular_season_column]
    won = team_game_data[won_column] * played

    def totalled_before(counted: pd.Series) -> pd.Series:
        """Exclusive, so a game is never part of the record it is measured against."""

        return counted.groupby(team_and_season, sort=False).cumsum() - counted

    games_played = totalled_before(played)
    team_game_data[SEASON_GAME_NUMBER] = games_played
    team_game_data[TEAM_WIN_PERCENTAGE] = (
        (totalled_before(won) / games_played).fillna(EVEN_RECORD).astype(BUILT_COLUMN_TYPE)
    )
    team_game_data[DAYS_INTO_SEASON] = (
        game_dates - game_dates.groupby(team_and_season, sort=False).transform('min')
    ).dt.days
    return team_game_data
