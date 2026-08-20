"""
What a team's core roster is worth going into a game.

A stored team row is a box score and says nothing about who played it, so who a team had available is
read out of the player box scores here and attached to the team's row. That is what lets a team or a
game model answer differently when a side is missing a star, and what lets a reader say who is out.

Only what a player was averaging before a game is read, so a game not yet played is read exactly like
a played one, out of the roster a request named. What the three readings mean is in
feature_engineering/roster_columns.py.

A training build reads every stored game. A prediction reads only the handful of games that decide
the two rows standing for the game being predicted, which is what keeps a request cheap: the rest of
the build never looks at these columns on any other row.
"""

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
"""How many of a player's recent games their averages are read over, which is about five weeks."""

PLAYER_HISTORY_YEARS = 3
"""
How far back a prediction reads a roster player's own games.

Only their last ROLLING_WINDOW games are averaged, so this has only to be long enough to still hold
them for somebody who has been out for most of a season.
"""

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
"""
The whole box score line a core player brings, which is what a team loses when they do not play.

Raw counts only. Points and total rebounds are sums of columns already here, and a derived column has
to beat what it is derived from before it earns its place. This is the same line the player models
total over the players around one player.
"""

def stat_columns() -> list[str]:
    """What a core player is measured in: their own recent average of each stat above."""

    return [PAST_MEAN_PREFIX + stat for stat in CORE_ROSTER_STATS]

def all_columns() -> list[str]:
    """Every column this adds to a team row, so a model can list what it reads without building it."""

    return roster_columns.core_roster_columns(stat_columns())

def _with_recent_means(player_game_data: pd.DataFrame) -> pd.DataFrame:
    """Each player game beside what that player was averaging going into it."""

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
    """
    The roster reading of every team game in the given frame.

    Neither frame needs to be sorted, and neither is modified. A team game with no player rows in the
    given player frame reads as a team that gained, lost and is missing nobody, so a caller narrowing
    either frame narrows what is worked out with it.
    """

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
    """Attaches the roster reading to each team game."""

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

# EVERY STORED GAME: #
def stored_totals(
    team_game_data: pd.DataFrame,
    window_start_date: date | None = None
    ) -> CoreRosterTotals:
    """
    The roster reading of every game in the given team frame, out of the stored player games.

    This is what a training build reads. The whole player archive is read rather than the roster of
    each game, because a player's recent average is worked out from their own run of games and a
    frame holding only some of them would average a career that never happened.
    """

    return totals_of(
        _complete_player_games(
            player_games.get_all_player_game_data() if window_start_date is None
            else player_games.get_game_data_after_date(window_start_date)
        ),
        team_game_data
    )

# THE GAME BEING PREDICTED: #
def recent_team_games(team_id: int, before: date) -> pd.DataFrame:
    """
    The team's last CORE_ROTATION_WINDOW complete games before the one being predicted, oldest first.

    The last of these is the lineup every build assumes a team is playing, so anything working out
    how that differs from who will actually play reads the same games from here.

    Exactly that many, because what a team normally has available is the average of those games and
    reading fewer would silently total a thinner team than the one a model was trained on. A build
    over stored games drops an incomplete row before it counts anything, so twice the window is read
    and cut back, rather than a row missing a column costing the window one of its games.
    """

    read = team_games.latest_games_before(
        team_id, before, roster_columns.CORE_ROTATION_WINDOW * 2
    )
    complete = season_columns.drop_incomplete_game_rows(read, team_games.SEASON_TYPE.category_name)

    return complete.tail(roster_columns.CORE_ROTATION_WINDOW).reset_index(drop=True)

def prediction_totals(
    target_game: Game,
    rosters: Mapping[int, RosterScenario]
    ) -> CoreRosterTotals:
    """
    The roster reading of the two rows standing for the game being predicted, and of nothing else.

    Each side plays whoever played its last game, less whoever the request says is out and plus
    whoever it says has joined. A player named as joining is read as a core player in a game nobody
    has played yet, which is what makes naming one change the answer.

    Only the games those two rows are measured against are read, so this costs a roster read and a
    few hundred player games rather than the whole league.

    Args:
        rosters is the change each side is making, keyed by team id. A side left out plays whoever
        played its last game.
    """

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
        """Who takes the floor for one side, which is its last lineup as the request changed it."""

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
