"""
Who a team has available for a game, measured against who it usually has.

A team is not the same team without its core players, and nothing in a box score says so. Three
readings do, each totalled over the same recent averages: who the team has just gained, who it has
just lost, and how much of what it normally has available is missing. The third is what carries a
star's whole absence rather than only the first game of it.

Two builds read these totals. A player row reads them as the players around one player, and a team
row reads them as its whole roster. The figures are the same either way, so they are worked out once
here and each build attaches them its own way. The only difference is that a player's own arrival is
taken back off their own row, because a player is not a teammate of themselves.

Everything here is worked out from the games in front of a row, so a game not yet played is read
exactly like a played one, out of a placeholder roster.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from nba_ml.feature_engineering.game_columns import BUILT_COLUMN_TYPE
from nba_ml.feature_engineering.schedule_columns import TEAM_GAME_NUMBER, number_team_games

GAINED_CORE_TEAMMATE_PREFIX = "GAINED_CORE_TEAMMATE_"
LOST_CORE_TEAMMATE_PREFIX = "LOST_CORE_TEAMMATE_"
ABSENT_CORE_TEAMMATE_PREFIX = "ABSENT_CORE_TEAMMATE_"
"""
What the three readings are called. Named from a player's point of view, because that is the build
they were written for and a column name is saved beside every model fit on it. A team row totals the
same thing over its whole roster.
"""

CORE_PLAYER_MINUTES_CUTOFF = 25
"""How many minutes a player has to be worth for their absence to be worth counting."""

CORE_ROTATION_WINDOW = 10
"""
How many of a team's last games decide what it normally has available.

A prediction has to read the roster of exactly these games, or the absent columns would total a
thinner team than the one the model was trained on.
"""

def core_roster_columns(stat_columns: list[str]) -> list[str]:
    """Every column these totals produce, so a model can list what it reads without building it."""

    return [
        prefix + column
        for prefix in (
            GAINED_CORE_TEAMMATE_PREFIX,
            LOST_CORE_TEAMMATE_PREFIX,
            ABSENT_CORE_TEAMMATE_PREFIX
        )
        for column in stat_columns
    ]

@dataclass(frozen=True)
class CoreRosterTotals():
    """The three readings per team game, and the part of the first that each arrival brought."""

    per_team_game: pd.DataFrame
    """One row per team game, indexed by game and team, holding core_roster_columns(stat_columns)."""

    gained_per_player: pd.DataFrame
    """
    What one player's own arrival added to their team's gained total, indexed by game, team and
    player. A player row subtracts its own so that a total says what is around the player.
    """

def core_roster_totals(
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
    ) -> CoreRosterTotals:
    """
    Totals each team game's gained, lost and missing core players over stat_columns.

    Those columns should hold what a player was averaging going into the game rather than what they
    did in it, so a total says what the team has, not what it got.

    Gained and lost compare a game's roster to the previous one. Absent is the shortfall against what
    the team normally had available over its last rotation_window games.

    Args:
        minutes_played_column decides who was core in a game that was played.
        recent_minutes_column decides who counts as core when only a roster is known, which is what
        a prediction has, so absent reads the same during training and during a prediction.

    team_game_data supplies the order of a team's games and needs its date column in datetime form.
    Neither frame needs to be sorted. A player game whose team game is not in the given team frame is
    left out, so a caller narrowing the team frame narrows what is read with it.
    """

    FOUND = "FOUND_IN_OTHER_GAME"

    team_games = number_team_games(
        team_game_data, game_id_column_team, team_id_column_team, game_date_column_team
    ).rename(columns={
        game_id_column_team: game_id_column_player,
        team_id_column_team: team_id_column_player
    })
    every_team_game = pd.MultiIndex.from_frame(team_games[[team_id_column_player, TEAM_GAME_NUMBER]])

    read_columns = [
        player_id_column,
        game_id_column_player,
        team_id_column_player,
        minutes_played_column,
        recent_minutes_column
    ]
    read_columns += [column for column in stat_columns if column not in read_columns]

    roster = player_game_data[read_columns].copy()
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

    gained = missing_from(
        core[[game_id_column_player] + keys + stat_columns],
        keyed_to_next_game(roster, [])
    )
    lost = missing_from(keyed_to_next_game(core, stat_columns), roster)

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

    def totalled(rows: pd.DataFrame) -> np.ndarray:
        """One reading laid out over every team game, in the order team_games holds them."""

        return rows.reindex(every_team_game).fillna(0).to_numpy(dtype=BUILT_COLUMN_TYPE)

    return CoreRosterTotals(
        per_team_game=pd.DataFrame(
            np.hstack([
                totalled(totals_per_game(gained)),
                totalled(totals_per_game(lost)),
                totalled(absent)
            ]),
            index=pd.MultiIndex.from_frame(
                team_games[[game_id_column_player, team_id_column_player]]
            ),
            columns=core_roster_columns(stat_columns)
        ),
        gained_per_player=gained.set_index(
            [game_id_column_player, team_id_column_player, player_id_column]
        )[stat_columns]
    )

def add_core_teammate_columns(
    player_game_data: pd.DataFrame,
    totals: CoreRosterTotals,
    player_id_column: str,
    game_id_column: str,
    team_id_column: str,
    stat_columns: list[str]
    ) -> pd.DataFrame:
    """
    Attaches the three readings to each player game, leaving the player's own arrival out of them.

    Gained says who joined the team around this player, so a player's own first game with the team
    must not count itself. Lost and absent are about players who are not on the row at all, so
    neither needs the same treatment.
    """

    team_key = pd.MultiIndex.from_arrays([
        player_game_data[game_id_column],
        player_game_data[team_id_column]
    ])
    values = totals.per_team_game.reindex(team_key).fillna(0.0).to_numpy(dtype=BUILT_COLUMN_TYPE)

    own_key = pd.MultiIndex.from_arrays([
        player_game_data[game_id_column],
        player_game_data[team_id_column],
        player_game_data[player_id_column]
    ])
    values[:, :len(stat_columns)] -= (
        totals.gained_per_player.reindex(own_key).fillna(0.0).to_numpy(dtype=BUILT_COLUMN_TYPE)
    )

    return pd.concat(
        [
            player_game_data,
            pd.DataFrame(
                values,
                index=player_game_data.index,
                columns=core_roster_columns(stat_columns)
            )
        ],
        axis=1
    )

def add_team_columns(
    team_game_data: pd.DataFrame,
    totals: CoreRosterTotals,
    game_id_column: str,
    team_id_column: str,
    stat_columns: list[str]
    ) -> pd.DataFrame:
    """
    Attaches the three readings to each team game.

    A team game the given totals say nothing about reads as a team with nobody gained, lost or
    missing. That is what a prediction hands over: only the rows it actually reads are worked out,
    because the rest of the build never looks at these columns on any other row.
    """

    key = pd.MultiIndex.from_arrays([
        team_game_data[game_id_column],
        team_game_data[team_id_column]
    ])

    return pd.concat(
        [
            team_game_data,
            pd.DataFrame(
                totals.per_team_game.reindex(key).fillna(0.0).to_numpy(dtype=BUILT_COLUMN_TYPE),
                index=team_game_data.index,
                columns=core_roster_columns(stat_columns)
            )
        ],
        axis=1
    )
