"""Player-specific feature columns, and the merge of player rows with team rows."""

import pandas as pd

from nba_ml.feature_engineering.game_columns import BUILT_COLUMN_TYPE, column_or_grouped_column
from nba_ml.feature_engineering.schedule_columns import TEAM_GAME_NUMBER, number_team_games

CHANGED_TEAM = 'CHANGED_TEAM'
def add_changed_team_column(
    player_game_data: pd.DataFrame,
    team_id_column: str,
    group_by_column: str | None = None
    ) -> pd.DataFrame:
    """The given game_data must be sorted by game date and grouped by player id."""

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
    """Adds the team games a player missed before each game and their recent availability."""

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
    """The date_entered_league and game_date columns must be in datetime form."""

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
    """Merges each player game row with their team's row for the same game."""

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
    """Converts heights written as feet-inches (e.g. 6-7) to inches."""

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
    """Converts the weight column to numbers. Unknown weights become NaN."""

    player_info[weight_column] = pd.to_numeric(player_info[weight_column], errors='coerce')

    if fill_unknown_with_mean:
        player_info[weight_column] = player_info[weight_column].fillna(player_info[weight_column].mean())

    return player_info

UNDRAFTED = 'Undrafted'
def encode_undrafted(
    player_info: pd.DataFrame,
    draft_number_column: str,
    ) -> pd.DataFrame:
    """Converts the draft number to a number and adds a flag column for undrafted players."""

    draft_number = pd.to_numeric(player_info[draft_number_column], errors='coerce')
    player_info[UNDRAFTED] = draft_number.isna().astype(int)
    player_info[draft_number_column] = draft_number.fillna(0)
    return player_info
