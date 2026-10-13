"""Features for the core players a team gained, lost or is missing compared to its recent games."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from nba_ml.feature_engineering.game_columns import BUILT_COLUMN_TYPE
from nba_ml.feature_engineering.schedule_columns import TEAM_GAME_NUMBER, number_team_games

GAINED_CORE_TEAMMATE_PREFIX = "GAINED_CORE_TEAMMATE_"
LOST_CORE_TEAMMATE_PREFIX = "LOST_CORE_TEAMMATE_"
ABSENT_CORE_TEAMMATE_PREFIX = "ABSENT_CORE_TEAMMATE_"

CORE_PLAYER_MINUTES_CUTOFF = 25
"""Minimum minutes for a player to count as a core player."""

CORE_ROTATION_WINDOW = 10
"""Number of recent team games used to determine a team's usual core roster."""

def core_roster_columns(stat_columns: list[str]) -> list[str]:
    """Returns the names of the gained, lost and absent columns for the given stats."""

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
    """Gained, lost and absent core player totals for each team game."""

    per_team_game: pd.DataFrame
    """One row per team game, indexed by game and team, with the core_roster_columns(stat_columns) columns."""

    gained_per_player: pd.DataFrame
    """Each gained player's own contribution to their team's gained totals."""

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
    """Sums stat_columns over the core players each team gained, lost and is missing in every game."""

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
        """Returns the rows with the team game number moved forward by one, to line up with the next game."""

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
        """Reindexes the totals to every team game, filling missing ones with 0."""

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
    """Adds the core roster columns to each player game row, excluding the player's own gained totals."""

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
    """Adds the core roster columns to each team game row."""

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
