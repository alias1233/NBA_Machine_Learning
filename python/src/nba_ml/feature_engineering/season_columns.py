"""Season feature columns: season type, progress through the season and team record."""

import pandas as pd

from nba_ml.feature_engineering.game_columns import BUILT_COLUMN_TYPE, encode_equality_as_integer
from nba_ml.season import GAME_ID_PREFIXES, SEASON_START_MONTH, SeasonType

def season_of(game_dates: pd.Series) -> pd.Series:
    """Returns the starting year of each game's season."""

    return game_dates.dt.year - (game_dates.dt.month < SEASON_START_MONTH)

### SEASON TYPES: A value of 1 represents True, and a value of 0 represents False. ###
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
"""Column with the season type as the one-character game ID prefix."""

def drop_incomplete_game_rows(
    game_data: pd.DataFrame,
    stored_season_type_column: str,
    optional_columns: tuple[str, ...] = ()
    ) -> pd.DataFrame:
    """Drops rows with missing values. A missing season type is allowed since it can be inferred."""

    optional = {stored_season_type_column, *optional_columns}
    required = [column for column in game_data.columns if column not in optional]
    return game_data.dropna(subset=required)

def add_encoded_season_type_columns(
    team_game_data: pd.DataFrame,
    game_id_column: str,
    season_type_column: str | None = None
    ) -> pd.DataFrame:
    """Adds the season type columns. A missing season type is taken from the first digit of the game ID."""

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
    """Adds the season game number, days into the season and team win percentage columns."""

    game_dates = team_game_data[game_date_column]
    team_and_season = [team_game_data[team_id_column], season_of(game_dates)]
    played = team_game_data[regular_season_column]
    won = team_game_data[won_column] * played

    def totalled_before(counted: pd.Series) -> pd.Series:
        """Returns the running total before each game, not including the game itself."""

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
