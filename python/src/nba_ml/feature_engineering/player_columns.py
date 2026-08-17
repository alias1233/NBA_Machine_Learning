"""
What is true of one player: who they play with, how much of the schedule they have been there for,
what they carry into a game, and how their row joins their team's.

Everything here reads a player frame, and the ones that also take a team frame read it only for the
order a team's games came in.

Every builder takes column names rather than assuming them, so nothing here decides which columns a
model wants.
"""

import numpy as np
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

GAINED_CORE_TEAMMATE_PREFIX = "GAINED_CORE_TEAMMATE_"
LOST_CORE_TEAMMATE_PREFIX = "LOST_CORE_TEAMMATE_"
ABSENT_CORE_TEAMMATE_PREFIX = "ABSENT_CORE_TEAMMATE_"
CORE_PLAYER_MINUTES_CUTOFF = 25
CORE_ROTATION_WINDOW = 10
def get_core_teammate_columns(stat_columns: list[str]) -> list[str]:
    return [
        prefix + column
        for prefix in (GAINED_CORE_TEAMMATE_PREFIX, LOST_CORE_TEAMMATE_PREFIX, ABSENT_CORE_TEAMMATE_PREFIX)
        for column in stat_columns
    ]
def add_core_teammate_columns(
    player_game_data: pd.DataFrame,
    team_game_data: pd.DataFrame,
    player_id_column: str,
    game_id_column_player: str,
    team_id_column_player: str,
    minutes_played_column: str,
    recent_minutes_column: str,
    game_id_column_team: str,
    team_id_column_team: str,
    game_date_column_team: str,
    stat_columns: list[str],
    rotation_window: int = CORE_ROTATION_WINDOW
    ) -> pd.DataFrame:
    """
    Adds, per player game, three readings of the players around them, each totalled over
    stat_columns. Those columns should hold what a player was averaging going into the game rather
    than what they did in it, so a total says what the team has, not what it got.

    Gained and lost compare this game's roster to the previous one, and leave the player's own
    numbers out of their own row. Absent is the shortfall against what the team normally has
    available over its last rotation_window games, which is what carries a star's whole absence
    rather than only the first game of it.

    Args:
        minutes_played_column decides who was core in a game that was played.
        recent_minutes_column decides who counts as core when only a roster is known, which is what
        a prediction has, so absent reads the same during training and during a prediction.

    team_game_data supplies the order of a team's games and needs its date column in datetime form.
    Neither frame needs to be sorted.
    """

    FOUND = "FOUND_IN_OTHER_GAME"

    team_games = number_team_games(
        team_game_data, game_id_column_team, team_id_column_team, game_date_column_team
    ).rename(columns={game_id_column_team: game_id_column_player, team_id_column_team: team_id_column_player})
    every_team_game = pd.MultiIndex.from_frame(team_games[[team_id_column_player, TEAM_GAME_NUMBER]])

    roster_columns = [player_id_column, team_id_column_player, minutes_played_column, recent_minutes_column]
    roster_columns += [column for column in stat_columns if column not in roster_columns]

    roster = player_game_data[roster_columns].copy()
    roster[TEAM_GAME_NUMBER] = (
        team_games.set_index([game_id_column_player, team_id_column_player])[TEAM_GAME_NUMBER]
        .reindex(pd.MultiIndex.from_arrays([
            player_game_data[game_id_column_player],
            player_game_data[team_id_column_player]
        ]))
        .to_numpy()
    )
    roster = roster.dropna(subset=[TEAM_GAME_NUMBER])
    roster[TEAM_GAME_NUMBER] = roster[TEAM_GAME_NUMBER].astype(np.int64)

    keys = [team_id_column_player, player_id_column, TEAM_GAME_NUMBER]
    core = roster[roster[minutes_played_column] >= CORE_PLAYER_MINUTES_CUTOFF]
    team_key = pd.MultiIndex.from_arrays([roster[team_id_column_player], roster[TEAM_GAME_NUMBER]])

    def keyed_to_next_game(rows: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """The given rows, renumbered so they line up with the game that came after them."""

        rows = rows[keys + columns].copy()
        rows[TEAM_GAME_NUMBER] += 1
        return rows

    def missing_from(rows: pd.DataFrame, other_game: pd.DataFrame) -> pd.DataFrame:
        found = other_game[keys].assign(**{FOUND: True})
        merged = rows.merge(found, on=keys, how='left')
        return merged[merged[FOUND].isna()]

    def totals_per_game(rows: pd.DataFrame) -> pd.DataFrame:
        return rows.groupby(by=[team_id_column_player, TEAM_GAME_NUMBER], sort=False)[stat_columns].sum()

    gained = missing_from(core[keys + stat_columns], keyed_to_next_game(roster, []))
    lost = missing_from(keyed_to_next_game(core, stat_columns), roster)

    own_gained = gained.set_index(keys)[stat_columns].reindex(pd.MultiIndex.from_frame(roster[keys])).fillna(0)

    # Every team game in order, so a team's rolling level below reads consecutive games even when a
    # game had nobody the roster counts as core.
    present = totals_per_game(roster[roster[recent_minutes_column] >= CORE_PLAYER_MINUTES_CUTOFF])
    present = present.reindex(every_team_game).fillna(0.0).sort_index()
    usual = (
        present.groupby(level=team_id_column_player, sort=False).shift(1)
        .groupby(level=team_id_column_player, sort=False)
        .rolling(rotation_window, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )
    absent = (usual - present).clip(lower=0)

    # Cast a reading at a time rather than the three together, so the widest thing held here is one
    # of them rather than all of them twice over.
    def totalled(rows: pd.DataFrame) -> np.ndarray:
        return totals_per_game(rows).reindex(team_key).fillna(0).to_numpy(dtype=BUILT_COLUMN_TYPE)

    columns = pd.DataFrame(
        np.hstack([
            totalled(gained) - own_gained.to_numpy(dtype=BUILT_COLUMN_TYPE),
            totalled(lost),
            absent.reindex(team_key).fillna(0).to_numpy(dtype=BUILT_COLUMN_TYPE)
        ]),
        index=roster.index,
        columns=get_core_teammate_columns(stat_columns)
    )

    return pd.concat([player_game_data, columns.reindex(player_game_data.index, fill_value=0.0)], axis=1)

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
