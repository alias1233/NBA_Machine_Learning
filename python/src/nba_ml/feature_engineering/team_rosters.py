"""Builds the core roster columns for team game rows."""

from datetime import date
from typing import Mapping

import pandas as pd
from dateutil.relativedelta import relativedelta

from nba_ml.entities import Game, RosterScenario
from nba_ml.feature_engineering import placeholders, rolling, roster_columns, season_columns
from nba_ml.feature_engineering.rolling import RollingCategory
from nba_ml.feature_engineering.roster_columns import CoreRosterTotals
from nba_ml.stores import player_games, team_games

ROLLING_WINDOW = 15
"""Number of recent games used for a player's rolling averages."""

PLAYER_HISTORY_YEARS = 3
"""Years of player game history loaded for a prediction."""

PAST_MEAN_PREFIX = "PAST_MEAN_"

CORE_ROSTER_STATS = [
    player_games.MINUTES_PLAYED.category_name,
    player_games.FIELD_GOALS_MADE.category_name,
    player_games.FIELD_GOALS_ATTEMPTED.category_name,
    player_games.THREE_POINTERS_MADE.category_name,
    player_games.THREE_POINTERS_ATTEMPTED.category_name,
    player_games.FREE_THROWS_MADE.category_name,
    player_games.FREE_THROWS_ATTEMPTED.category_name,
    player_games.OFFENSIVE_REBOUNDS.category_name,
    player_games.DEFENSIVE_REBOUNDS.category_name,
    player_games.ASSISTS.category_name,
    player_games.TURNOVERS.category_name,
    player_games.STEALS.category_name,
    player_games.BLOCKS.category_name,
    player_games.PERSONAL_FOULS.category_name
]
"""The box score stats summed over core players."""

def stat_columns() -> list[str]:
    """Returns the rolling mean column name for each core roster stat."""

    return [PAST_MEAN_PREFIX + stat for stat in CORE_ROSTER_STATS]

def all_columns() -> list[str]:
    """Returns the names of every column this module adds to a team row."""

    return roster_columns.core_roster_columns(stat_columns())

def _with_recent_means(player_game_data: pd.DataFrame) -> pd.DataFrame:
    """Adds each player's rolling averages going into each game."""

    player_game_data = player_game_data.copy()
    player_game_data[player_games.GAME_DATE.category_name] = pd.to_datetime(
        player_game_data[player_games.GAME_DATE.category_name]
    )
    player_game_data = player_game_data.sort_values(
        by=[player_games.PLAYER_ID.category_name, player_games.GAME_DATE.category_name]
    ).reset_index(drop=True)

    return rolling.add_rolling_function_columns(
        player_game_data,
        [
            RollingCategory(PAST_MEAN_PREFIX + stat, stat, rolling.MEAN_FUNCTION, ROLLING_WINDOW)
            for stat in CORE_ROSTER_STATS
        ],
        group_by_column=player_games.PLAYER_ID.category_name
    )

def totals_of(player_game_data: pd.DataFrame, team_game_data: pd.DataFrame) -> CoreRosterTotals:
    """Returns the core roster totals for every team game in the given data."""

    team_game_data = team_game_data.copy()
    team_game_data[team_games.GAME_DATE.category_name] = pd.to_datetime(
        team_game_data[team_games.GAME_DATE.category_name]
    )

    return roster_columns.core_roster_totals(
        _with_recent_means(player_game_data),
        team_game_data,
        player_games.PLAYER_ID.category_name,
        player_games.GAME_ID.category_name,
        player_games.TEAM_ID.category_name,
        player_games.MINUTES_PLAYED.category_name,
        PAST_MEAN_PREFIX + player_games.MINUTES_PLAYED.category_name,
        team_games.GAME_ID.category_name,
        team_games.TEAM_ID.category_name,
        team_games.GAME_DATE.category_name,
        stat_columns()
    )

def add_columns(team_game_data: pd.DataFrame, totals: CoreRosterTotals) -> pd.DataFrame:
    return roster_columns.add_team_columns(
        team_game_data,
        totals,
        team_games.GAME_ID.category_name,
        team_games.TEAM_ID.category_name,
        stat_columns()
    )

def _complete_player_games(player_game_data: pd.DataFrame) -> pd.DataFrame:
    return season_columns.drop_incomplete_game_rows(
        player_game_data,
        player_games.SEASON_TYPE.category_name
    )

# STORED GAMES: #
def stored_totals(
    team_game_data: pd.DataFrame,
    window_start_date: date | None = None
    ) -> CoreRosterTotals:
    """Returns the core roster totals for the given team games, using the stored player games."""

    return totals_of(
        _complete_player_games(
            player_games.get_all_player_game_data() if window_start_date is None
            else player_games.get_game_data_after_date(window_start_date)
        ),
        team_game_data
    )

# TARGET GAME: #
def recent_team_games(team_id: int, before: date) -> pd.DataFrame:
    """Returns the team's last CORE_ROTATION_WINDOW complete games before the given date, oldest first."""

    # Load twice the window, since incomplete rows are dropped before trimming to the window.
    read = team_games.latest_games_before(
        team_id, before, roster_columns.CORE_ROTATION_WINDOW * 2
    )
    complete = season_columns.drop_incomplete_game_rows(read, team_games.SEASON_TYPE.category_name)

    return complete.tail(roster_columns.CORE_ROTATION_WINDOW).reset_index(drop=True)

def prediction_totals(
    target_game: Game,
    rosters: Mapping[int, RosterScenario]
    ) -> CoreRosterTotals:
    """Returns the core roster totals for both teams in the game being predicted."""

    played = {
        team_id: recent_team_games(team_id, target_game.date)
        for team_id in target_game.team_ids
    }
    scenarios = {
        team_id: rosters.get(team_id, RosterScenario()) for team_id in target_game.team_ids
    }

    roster_player_ids: set[int] = set()
    for team_id, games in played.items():
        roster_player_ids |= player_games.player_ids_in_games(
            team_id,
            games[team_games.GAME_ID.category_name].tolist()
        )
        roster_player_ids |= set(scenarios[team_id].returning)

    player_game_data = _complete_player_games(
        player_games.get_players_game_data(
            roster_player_ids,
            target_game.date - relativedelta(years=PLAYER_HISTORY_YEARS)
        )
    )

    def playing_in(team_id: int) -> set[int]:
        games = played[team_id]
        scenario = scenarios[team_id]
        last_lineup: set[int] = set()

        if not games.empty:
            last_game_id = games[team_games.GAME_ID.category_name].iloc[-1]
            last_lineup = set(
                player_game_data[
                    (player_game_data[player_games.TEAM_ID.category_name] == team_id)
                    & (player_game_data[player_games.GAME_ID.category_name] == last_game_id)
                ][player_games.PLAYER_ID.category_name]
            )

        return (last_lineup | set(scenario.returning)) - set(scenario.without)

    return totals_of(
        pd.concat(
            [player_game_data] + [
                placeholders.player_rows(
                    target_game,
                    team_id,
                    playing_in(team_id),
                    scenarios[team_id].returning
                )
                for team_id in target_game.team_ids
            ],
            ignore_index=True
        ),
        pd.concat(
            list(played.values()) + [placeholders.game_rows(target_game)],
            ignore_index=True
        )
    )
