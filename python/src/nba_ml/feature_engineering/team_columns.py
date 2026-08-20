"""
What one team's line in a game says, and what pairing it with the other team's line adds.

A stored row holds one side of a game. The result, the total and everything a team allowed only
exist once the two sides sit on the same row, which is what the opponent columns here are for.

Every builder takes column names rather than assuming them, so a caller decides which columns are
worth carrying over.
"""

import pandas as pd

from nba_ml.feature_engineering import game_columns
from nba_ml.feature_engineering.game_columns import BUILT_COLUMN_TYPE, encode_equality_as_integer

POSSESSIONS = 'POSSESSIONS'
def add_possessions_column(
    team_game_data: pd.DataFrame,
    fga_column: str,
    fta_column: str,
    orb_column: str,
    tov_column: str
    ) -> pd.DataFrame:
    fga = team_game_data[fga_column]
    fta = team_game_data[fta_column]
    orb = team_game_data[orb_column]
    tov = team_game_data[tov_column]
    team_game_data[POSSESSIONS] = (fga + (0.44 * fta) - orb + tov).astype(BUILT_COLUMN_TYPE)
    return team_game_data

POINT_DIFFERENTIAL = 'POINT_DIFFERENTIAL'
def add_point_differential_column(
    team_game_data: pd.DataFrame,
    points_column: str,
    opponent_points_column: str
    ) -> pd.DataFrame:
    """
    How much the team won or lost the game by.

    The opposing team's points have to be on the row already, so this runs after they are copied over.
    """

    team_game_data[POINT_DIFFERENTIAL] = (
        team_game_data[points_column] - team_game_data[opponent_points_column]
    )
    return team_game_data

COMBINED_PREFIX = 'TOTAL_'
def combined_column(stat: str) -> str:
    """What both teams recorded together, which is the column a game total is read off."""

    return COMBINED_PREFIX + stat

GAME_TOTAL = combined_column(game_columns.POINTS)
"""The points both teams scored together, named because so much reads it."""

def add_combined_stat_columns(
    team_game_data: pd.DataFrame,
    stats: list[str]
    ) -> pd.DataFrame:
    """
    Adds what both teams recorded together for each of the given stats.

    Each needs the opposing team's own line already on the row, so this runs after it is copied over.
    A combined stat is the same number on both rows of a game, which is what makes it a statistic of
    the game rather than of either side.
    """

    for stat in stats:
        team_game_data[combined_column(stat)] = (
            team_game_data[stat] + team_game_data[OPPONENT_PREFIX + stat]
        )
    return team_game_data

def encode_win_loss_column_as_integer(
    game_data: pd.DataFrame,
    win_loss_column: str
    ) -> pd.DataFrame:
    """Rewrites the win/loss column as one for a win and zero for a loss."""

    game_data[win_loss_column] = encode_equality_as_integer(game_data[win_loss_column], "W")
    return game_data

# A value of 0 represents home, and a value of 1 represents away.
HOME_OR_AWAY = 'HOME_OR_AWAY'
HOME = "HOME"
AWAY = "AWAY"
# The raw data writes the away team's game as "ATL @ DET" and the home team's as "DET vs. ATL".
HOME_OR_AWAY_ENCODING = {
    HOME : "vs.",
    AWAY : '@'
}
def add_encoded_home_or_away_column(
    team_game_data: pd.DataFrame,
    matchup_column: str
    ) -> pd.DataFrame:
    matchup = team_game_data[matchup_column]
    home_or_away = pd.Series(index=matchup.index, dtype='Int64')
    home_or_away[matchup.str.contains(HOME_OR_AWAY_ENCODING[AWAY], regex=False, na=False)] = 1
    home_or_away[matchup.str.contains(HOME_OR_AWAY_ENCODING[HOME], regex=False, na=False)] = 0
    team_game_data[HOME_OR_AWAY] = home_or_away
    return team_game_data

OPPONENT_PREFIX = 'OPP_'
def add_opponent_stat_columns(
    team_game_data: pd.DataFrame,
    game_id_column: str,
    team_id_column: str,
    columns_to_copy: list[str]
    ) -> pd.DataFrame:
    """
    Adds the other team's stats to each row under the opponent prefix.

    Only columns_to_copy are copied. This frame is the widest in the pipeline, so copying all of it
    would roughly double the peak memory for columns that are never read back. The team id is always
    copied, because it is what pairs the two rows of a game up.

    Calling this again replaces what an earlier call copied rather than colliding with it, which is
    what lets a build copy raw stats, roll windows over them, and then copy those windows too.
    """

    opponent_columns = [team_id_column] + [column for column in columns_to_copy if column != team_id_column]
    copied_column_names = {column: OPPONENT_PREFIX + column for column in opponent_columns}
    opponent_stats = team_game_data[[game_id_column] + opponent_columns].rename(columns=copied_column_names)

    merged = team_game_data.drop(columns=list(copied_column_names.values()), errors='ignore').merge(
        opponent_stats, on=game_id_column
    )
    return merged[merged[team_id_column] != merged[OPPONENT_PREFIX + team_id_column]]
