"""
What is true of one player: who they play with, how much of the schedule they have been there for,
what they carry into a game, and how their row joins their team's.

Everything here reads a player frame, and the ones that also take a team frame read it only for the
order a team's games came in.

Every builder takes column names rather than assuming them, so nothing here decides which columns a
model wants.
"""

import pandas as pd

from nba_ml.feature_engineering.game_columns import BUILT_COLUMN_TYPE, column_or_grouped_column
from nba_ml.feature_engineering.schedule_columns import TEAM_GAME_NUMBER, number_team_games

CHANGED_TEAM = 'CHANGED_TEAM'
def add_changed_team_column(
    player_game_data: pd.DataFrame,
    team_id_column: str,
    group_by_column: str | None = None
    ) -> pd.DataFrame:
    """
    The given game_data must be sorted by game date and grouped by player id.

    Args:
        group_by_column covers every group in one pass. Without it the frame must hold one group.
    """

    team_id = player_game_data[team_id_column]
    previous_team_id = column_or_grouped_column(player_game_data, team_id_column, group_by_column).shift(1)
    player_game_data[CHANGED_TEAM] = ((team_id != previous_team_id) & previous_team_id.notna()).astype(int)
    return player_game_data

TEAM_GAMES_MISSED = 'TEAM_GAMES_MISSED'
RECENT_AVAILABILITY = 'RECENT_AVAILABILITY'
ALL_AVAILABILITY_COLUMNS = [TEAM_GAMES_MISSED, RECENT_AVAILABILITY]
AVAILABILITY_WINDOW = 10
MAX_TEAM_GAMES_MISSED = 15
def add_availability_columns(
    player_game_data: pd.DataFrame,
    team_game_data: pd.DataFrame,
    player_id_column: str,
    game_id_column_player: str,
    team_id_column_player: str,
    game_id_column_team: str,
    team_id_column_team: str,
    game_date_column_team: str,
    window: int = AVAILABILITY_WINDOW,
    max_games_missed: int = MAX_TEAM_GAMES_MISSED
    ) -> pd.DataFrame:
    """
    Adds how much of their team's recent schedule the player has been available for. Rest only sees
    the gap in days, so a player in and out of the lineup reads as well rested without these.

    TEAM_GAMES_MISSED is how many games the team played since the player last appeared for them.
    RECENT_AVAILABILITY is the share of its games the player played over their last window
    appearances. Both are unknown until the player has a history with the team, and an unknown reads
    as fully available.

    Neither frame needs to be sorted. team_game_data supplies the order of a team's games and needs
    its date column in datetime form.
    """

    numbered = number_team_games(
        team_game_data, game_id_column_team, team_id_column_team, game_date_column_team
    ).rename(columns={game_id_column_team: game_id_column_player, team_id_column_team: team_id_column_player})

    appearances = player_game_data[[player_id_column, game_id_column_player, team_id_column_player]].merge(
        numbered, on=[game_id_column_player, team_id_column_player], how='left'
    )
    appearances.index = player_game_data.index
    appearances = appearances.sort_values(by=[player_id_column, team_id_column_player, TEAM_GAME_NUMBER])

    spell = appearances.groupby(by=[player_id_column, team_id_column_player], sort=False)[TEAM_GAME_NUMBER]
    game_number = appearances[TEAM_GAME_NUMBER]

    missed = (game_number - spell.shift(1) - 1).fillna(0).clip(lower=0, upper=max_games_missed)
    # Games the team played across the player's last window appearances. Equal to the window when
    # they played every one of them, and larger by however many they sat out.
    played_over = game_number - spell.shift(window)

    player_game_data[TEAM_GAMES_MISSED] = missed.reindex(player_game_data.index).astype(BUILT_COLUMN_TYPE)
    player_game_data[RECENT_AVAILABILITY] = (
        (window / played_over).clip(upper=1.0).fillna(1.0).reindex(player_game_data.index)
    ).astype(BUILT_COLUMN_TYPE)
    return player_game_data

NBA_EXPERIENCE_DURING_GAME = 'NBA_EXPERIENCE_DURING_GAME'
def add_years_NBA_experience_during_game_column(
    game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_player_info: str,
    player_id_column_game_data: str,
    date_entered_league_column: str,
    game_date_column: str
    ) -> pd.DataFrame:
    """
    The date_entered_league and game_date columns must be represented in datetime form.
    """

    entered = player_info.set_index(player_id_column_player_info)[date_entered_league_column]
    game_data[NBA_EXPERIENCE_DURING_GAME] = (
        game_data[game_date_column]
        - game_data[player_id_column_game_data].map(entered, na_action="ignore")
    ).dt.days.div(365.25).astype(BUILT_COLUMN_TYPE)
    return game_data

PLAYER_SUFFIX = '_PLAYER'
TEAM_SUFFIX = '_TEAM'
def merge_player_team_game_data(
    player_game_data: pd.DataFrame,
    team_game_data: pd.DataFrame,
    game_id_column_team: str,
    game_id_column_player: str,
    team_id_column_team: str,
    team_id_column_player: str,
    duplicate_categories_player: list[str] | None = None,
    ) -> pd.DataFrame:
    """
    Joins each player's game row onto their own team's row for that game.

    The team is joined on as well as the game, so a player row meets one team row rather than both
    sides of the game and then being cut back to one. This is the widest frame the whole pipeline
    builds, and joining on the game alone made it twice the size it ends up.

    Args:
        duplicate_categories_player names player columns the team frame also holds, which are
        dropped rather than suffixed.
    """

    non_duplicate_player_game_data = player_game_data.drop(columns=duplicate_categories_player or [], errors='ignore')

    return non_duplicate_player_game_data.merge(
        team_game_data,
        left_on=[game_id_column_player, team_id_column_player],
        right_on=[game_id_column_team, team_id_column_team],
        suffixes=(PLAYER_SUFFIX, TEAM_SUFFIX)
    )

def convert_height_to_inches(
    player_info: pd.DataFrame,
    height_column: str,
    fill_unknown_with_mean: bool = False
    ) -> pd.DataFrame:
    """Rewrites a height written as feet-inches, such as 6-7, as a number of inches."""

    heights_split = player_info[height_column].str.split("-", expand=True)
    feet = pd.to_numeric(heights_split[0], errors="coerce")
    inches = pd.to_numeric(heights_split[1], errors="coerce")
    player_info[height_column] = feet * 12 + inches

    if fill_unknown_with_mean:
        player_info[height_column] = player_info[height_column].fillna(player_info[height_column].mean())

    return player_info

def handle_unknown_weight(
    player_info: pd.DataFrame,
    weight_column: str,
    fill_unknown_with_mean: bool = False
    ) -> pd.DataFrame:
    """Makes the weight column a number, since an unknown weight arrives as empty text."""

    player_info[weight_column] = pd.to_numeric(player_info[weight_column], errors='coerce')

    if fill_unknown_with_mean:
        player_info[weight_column] = player_info[weight_column].fillna(player_info[weight_column].mean())

    return player_info

UNDRAFTED = 'Undrafted'
def encode_undrafted(
    player_info: pd.DataFrame,
    draft_number_column: str,
    ) -> pd.DataFrame:
    """
    Makes the draft number a number, with a flag beside it for a player who was not drafted.

    Anything that is not a draft position reads as undrafted, whichever way it was written. The data
    source writes the word for a player it holds no draft record of, and the older nba.com archive
    leaves the column empty for one, so both eras have to say the same thing about the same player.
    Left as it was, an empty one reached a model as a blank and turned every loss into nan.
    """

    draft_number = pd.to_numeric(player_info[draft_number_column], errors='coerce')
    player_info[UNDRAFTED] = draft_number.isna().astype(int)
    player_info[draft_number_column] = draft_number.fillna(0)
    return player_info
