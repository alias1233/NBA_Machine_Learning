"""Team feature columns, including ones that combine a team's stats with its opponent's."""

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
    """Adds the team's margin of victory or defeat. The opponent's points must already be on the row."""

    team_game_data[POINT_DIFFERENTIAL] = (
        team_game_data[points_column] - team_game_data[opponent_points_column]
    )
    return team_game_data

COMBINED_PREFIX = 'TOTAL_'
def combined_column(stat: str) -> str:
    """Returns the name of the column with both teams' combined total of a stat."""

    return COMBINED_PREFIX + stat

GAME_TOTAL = combined_column(game_columns.POINTS)
"""Column with both teams' combined points."""

def add_combined_stat_columns(
    team_game_data: pd.DataFrame,
    stats: list[str]
    ) -> pd.DataFrame:
    """Adds a combined total of both teams for each of the given stats."""

    for stat in stats:
        team_game_data[combined_column(stat)] = (
            team_game_data[stat] + team_game_data[OPPONENT_PREFIX + stat]
        )
    return team_game_data

def encode_win_loss_column_as_integer(
    game_data: pd.DataFrame,
    win_loss_column: str
    ) -> pd.DataFrame:
    """Converts the win/loss column to 1 for a win and 0 for a loss."""

    game_data[win_loss_column] = encode_equality_as_integer(game_data[win_loss_column], "W")
    return game_data

# A value of 0 represents home, and a value of 1 represents away.
HOME_OR_AWAY = 'HOME_OR_AWAY'
HOME = "HOME"
AWAY = "AWAY"
# The raw matchup is "ATL @ DET" for the away team and "DET vs. ATL" for the home team.
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
    """Adds the opponent's stats to each row, with the opponent prefix."""

    opponent_columns = [team_id_column] + [column for column in columns_to_copy if column != team_id_column]
    copied_column_names = {column: OPPONENT_PREFIX + column for column in opponent_columns}
    opponent_stats = team_game_data[[game_id_column] + opponent_columns].rename(columns=copied_column_names)

    merged = team_game_data.drop(columns=list(copied_column_names.values()), errors='ignore').merge(
        opponent_stats, on=game_id_column
    )
    return merged[merged[team_id_column] != merged[OPPONENT_PREFIX + team_id_column]]
