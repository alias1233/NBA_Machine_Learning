"""Builds one feature row per team per game from the stored team box scores."""

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from nba_ml.entities import Game, RosterScenario
from nba_ml.feature_engineering import (
    game_columns,
    placeholders,
    rolling,
    schedule_columns,
    season_columns,
    situations,
    team_columns,
    team_rosters
)
from nba_ml.feature_engineering.roster_columns import CoreRosterTotals
from nba_ml.feature_engineering.rolling import RollingCategory
from nba_ml.feature_engineering.samples import OUTPUT, GameHistory, split_into_histories
from nba_ml.feature_engineering.situations import SituationalStat
from nba_ml.stores import team_games as team_game_store

ROLLING_WINDOW = 15
"""Number of recent games averaged by the rolling mean columns."""

# Halflife of the exponentially weighted mean columns, in games.
RECENT_FORM_HALFLIFE = 3

SEASON_WINDOW = 82
"""Window for the season-long mean and standard deviation columns. 82 games is one regular season."""

# Years of game history loaded for a prediction.
HISTORICAL_WINDOW_LENGTH_YEARS = 5

# Must be at least 1 because the model's input sequence can't be empty.
MINIMUM_PAST_GAMES = 1

PAST_MEAN_PREFIX = "PAST_MEAN_"
PAST_WEIGHTED_MEAN_PREFIX = "PAST_WEIGHTED_MEAN_"
PAST_SEASON_MEAN_PREFIX = "PAST_SEASON_MEAN_"
PAST_SEASON_STD_PREFIX = "PAST_SEASON_STD_"

# KEY COLUMNS: #
TEAM_ID = team_game_store.TEAM_ID.category_name
GAME_ID = team_game_store.GAME_ID.category_name
GAME_DATE = team_game_store.GAME_DATE.category_name
OPPONENT_TEAM_ID = team_columns.OPPONENT_PREFIX + TEAM_ID

# STAT COLUMNS: #
WIN = team_game_store.WIN_LOSS.category_name
"""The win/loss column. It is converted to 1 for a win and 0 for a loss."""

WON, LOST = 0, 1
"""Class indices of a win and a loss for the model that predicts the winner."""

WIN_CATEGORY = 'WIN_CATEGORY'
"""Column with the game result as one of the class indices above."""

IS_HOME_ROW = 'IS_HOME_ROW'
"""True on the home team's row. HOME_OR_AWAY is the opposite, with 1 for away."""

BOX_SCORE_STATS = [
    team_game_store.FIELD_GOALS_MADE.category_name,
    team_game_store.FIELD_GOALS_ATTEMPTED.category_name,
    team_game_store.THREE_POINTERS_MADE.category_name,
    team_game_store.THREE_POINTERS_ATTEMPTED.category_name,
    team_game_store.FREE_THROWS_MADE.category_name,
    team_game_store.FREE_THROWS_ATTEMPTED.category_name,
    team_game_store.OFFENSIVE_REBOUNDS.category_name,
    team_game_store.DEFENSIVE_REBOUNDS.category_name,
    team_game_store.ASSISTS.category_name,
    team_game_store.STEALS.category_name,
    team_game_store.BLOCKS.category_name,
    team_game_store.TURNOVERS.category_name,
    team_game_store.PERSONAL_FOULS.category_name
]

COPIED_FROM_THE_OTHER_SIDE = BOX_SCORE_STATS + [
    game_columns.POINTS,
    game_columns.REBOUNDS,
    team_columns.POSSESSIONS
]
"""Stats copied from the opponent's row onto each team's row."""

OWN_GAME_STATS = COPIED_FROM_THE_OTHER_SIDE + [
    team_game_store.MINUTES_PLAYED.category_name,
    WIN,
    team_columns.POINT_DIFFERENTIAL,
    team_columns.GAME_TOTAL
]

COMBINED_GAME_STATS = [
    game_columns.POINTS,
    game_columns.REBOUNDS,
    team_game_store.ASSISTS.category_name,
    team_game_store.THREE_POINTERS_MADE.category_name
]
"""Stats that get a combined total for both teams."""

ALLOWED_GAME_STATS = [
    team_columns.OPPONENT_PREFIX + stat for stat in COPIED_FROM_THE_OTHER_SIDE
]
"""The opponent's stats in the same game, which are what the team allowed."""

RECENT_FORM_STATS = [
    game_columns.POINTS,
    team_columns.POSSESSIONS,
    team_columns.POINT_DIFFERENTIAL,
    team_columns.GAME_TOTAL,
    WIN,
    team_game_store.THREE_POINTERS_ATTEMPTED.category_name,
    team_game_store.FREE_THROWS_ATTEMPTED.category_name,
    team_columns.OPPONENT_PREFIX + game_columns.POINTS,
    team_columns.OPPONENT_PREFIX + team_columns.POSSESSIONS
]
"""Stats that also get an exponentially weighted mean."""

SEASON_LEVEL_STATS = [
    game_columns.POINTS,
    team_columns.OPPONENT_PREFIX + game_columns.POINTS,
    team_columns.POINT_DIFFERENTIAL,
    team_columns.GAME_TOTAL,
    team_columns.POSSESSIONS
]
"""Stats that get a mean and standard deviation over the season window."""

CONTEXT_COLUMNS = [
    team_columns.HOME_OR_AWAY,
    schedule_columns.REST,
    schedule_columns.BREAK_LENGTH,
    schedule_columns.SEASON_OPENER
] + (
    season_columns.ALL_SEASON_TYPES
    + season_columns.ALL_SEASON_CONTEXT_COLUMNS
    + schedule_columns.get_recent_game_count_columns()
)
"""Schedule and season columns that are known before a game is played."""

OPPONENT_CONTEXT_STATS = [
    schedule_columns.REST,
    schedule_columns.BREAK_LENGTH,
    season_columns.SEASON_GAME_NUMBER,
    season_columns.TEAM_WIN_PERCENTAGE
] + schedule_columns.get_recent_game_count_columns()

SITUATIONS = [situations.IN_THIS_SEASON_TYPE, situations.AT_HOME_OR_AWAY]
"""Situations that team form is tracked for."""

READS_CORE_ROSTER = True
"""Whether rows include the core roster columns."""

def _allowed(stat: str) -> str:
    return team_columns.OPPONENT_PREFIX + stat

@dataclass(frozen=True)
class TargetColumns():
    """The output column for a target and the extra stats it needs on top of the defaults."""

    output_column: str

    mean_stats: tuple[str, ...] = ()
    """Extra stats to add a rolling mean for."""

    recent_form_stats: tuple[str, ...] = ()
    """Extra stats to add an exponentially weighted mean for."""

    season_level_stats: tuple[str, ...] = ()
    """Extra stats to add a season-long mean and standard deviation for."""

class TargetValue(Enum):
    """The values a team or game model can predict."""

    POINT_DIFFERENTIAL = TargetColumns(team_columns.POINT_DIFFERENTIAL)
    TEAM_POINTS = TargetColumns(game_columns.POINTS)
    GAME_TOTAL = TargetColumns(team_columns.GAME_TOTAL)
    RESULT = TargetColumns(WIN_CATEGORY)

    TEAM_REBOUNDS = TargetColumns(
        game_columns.REBOUNDS,
        recent_form_stats=(
            game_columns.REBOUNDS,
            team_game_store.OFFENSIVE_REBOUNDS.category_name,
            team_game_store.DEFENSIVE_REBOUNDS.category_name,
            team_game_store.FIELD_GOALS_ATTEMPTED.category_name,
            team_game_store.FIELD_GOALS_MADE.category_name,
            _allowed(team_game_store.FIELD_GOALS_ATTEMPTED.category_name),
            _allowed(team_game_store.FIELD_GOALS_MADE.category_name),
            _allowed(game_columns.REBOUNDS)
        ),
        season_level_stats=(game_columns.REBOUNDS, _allowed(game_columns.REBOUNDS))
    )

    TEAM_ASSISTS = TargetColumns(
        team_game_store.ASSISTS.category_name,
        recent_form_stats=(
            team_game_store.ASSISTS.category_name,
            team_game_store.FIELD_GOALS_MADE.category_name,
            team_game_store.THREE_POINTERS_MADE.category_name,
            _allowed(team_game_store.ASSISTS.category_name)
        ),
        season_level_stats=(
            team_game_store.ASSISTS.category_name,
            _allowed(team_game_store.ASSISTS.category_name)
        )
    )

    TEAM_THREE_POINTERS = TargetColumns(
        team_game_store.THREE_POINTERS_MADE.category_name,
        recent_form_stats=(
            team_game_store.THREE_POINTERS_MADE.category_name,
            team_game_store.FIELD_GOALS_ATTEMPTED.category_name,
            _allowed(team_game_store.THREE_POINTERS_MADE.category_name),
            _allowed(team_game_store.THREE_POINTERS_ATTEMPTED.category_name)
        ),
        season_level_stats=(
            team_game_store.THREE_POINTERS_MADE.category_name,
            _allowed(team_game_store.THREE_POINTERS_MADE.category_name)
        )
    )

    TOTAL_REBOUNDS = TargetColumns(
        team_columns.combined_column(game_columns.REBOUNDS),
        mean_stats=(team_columns.combined_column(game_columns.REBOUNDS),),
        recent_form_stats=(
            team_columns.combined_column(game_columns.REBOUNDS),
            game_columns.REBOUNDS,
            _allowed(game_columns.REBOUNDS),
            team_game_store.FIELD_GOALS_ATTEMPTED.category_name,
            _allowed(team_game_store.FIELD_GOALS_ATTEMPTED.category_name)
        ),
        season_level_stats=(
            team_columns.combined_column(game_columns.REBOUNDS),
            game_columns.REBOUNDS
        )
    )

    TOTAL_ASSISTS = TargetColumns(
        team_columns.combined_column(team_game_store.ASSISTS.category_name),
        mean_stats=(team_columns.combined_column(team_game_store.ASSISTS.category_name),),
        recent_form_stats=(
            team_columns.combined_column(team_game_store.ASSISTS.category_name),
            team_game_store.ASSISTS.category_name,
            _allowed(team_game_store.ASSISTS.category_name),
            team_game_store.FIELD_GOALS_MADE.category_name
        ),
        season_level_stats=(
            team_columns.combined_column(team_game_store.ASSISTS.category_name),
            team_game_store.ASSISTS.category_name
        )
    )

    TOTAL_THREE_POINTERS = TargetColumns(
        team_columns.combined_column(team_game_store.THREE_POINTERS_MADE.category_name),
        mean_stats=(team_columns.combined_column(team_game_store.THREE_POINTERS_MADE.category_name),),
        recent_form_stats=(
            team_columns.combined_column(team_game_store.THREE_POINTERS_MADE.category_name),
            team_game_store.THREE_POINTERS_MADE.category_name,
            _allowed(team_game_store.THREE_POINTERS_MADE.category_name),
            _allowed(team_game_store.THREE_POINTERS_ATTEMPTED.category_name)
        ),
        season_level_stats=(
            team_columns.combined_column(team_game_store.THREE_POINTERS_MADE.category_name),
            team_game_store.THREE_POINTERS_MADE.category_name
        )
    )

# FEATURE SETS: #
@dataclass(frozen=True)
class FeatureSet():
    """The columns and rolling definitions used by one model."""

    output_column: str

    rolling_categories: list[RollingCategory]
    situational_stats: list[SituationalStat]

    columns_copied_from_opponent: list[str]

    sequence_columns: list[str]
    """Columns taken from each of the team's past games."""

    static_columns: list[str]
    """Columns taken from the game being predicted."""

def build_feature_set(target: TargetValue, dropped_static_columns: tuple[str, ...] = ()) -> FeatureSet:
    columns = target.value

    def gather(always: list[str], selected: tuple[str, ...]) -> list[str]:
        return sorted(set(always) | set(selected))

    mean_stats = gather(
        OWN_GAME_STATS + ALLOWED_GAME_STATS,
        columns.mean_stats + columns.recent_form_stats + columns.season_level_stats
    )
    weighted_mean_stats = gather(RECENT_FORM_STATS, columns.recent_form_stats)
    season_level_stats = gather(SEASON_LEVEL_STATS, columns.season_level_stats)

    rolling_categories = (
        [
            RollingCategory(PAST_MEAN_PREFIX + stat, stat, rolling.MEAN_FUNCTION, ROLLING_WINDOW)
            for stat in mean_stats
        ] + [
            RollingCategory(
                PAST_WEIGHTED_MEAN_PREFIX + stat,
                stat,
                rolling.MEAN_FUNCTION,
                halflife=RECENT_FORM_HALFLIFE
            )
            for stat in weighted_mean_stats
        ] + [
            RollingCategory(PAST_SEASON_MEAN_PREFIX + stat, stat, rolling.MEAN_FUNCTION, SEASON_WINDOW)
            for stat in season_level_stats
        ] + [
            RollingCategory(PAST_SEASON_STD_PREFIX + stat, stat, rolling.STD_FUNCTION, SEASON_WINDOW)
            for stat in season_level_stats
        ]
    )

    situational_stats = [
        SituationalStat(stat, stat, PAST_MEAN_PREFIX + stat) for stat in season_level_stats
    ]
    situational_columns = situations.all_columns(SITUATIONS, situational_stats)

    core_roster_columns = team_rosters.all_columns() if READS_CORE_ROSTER else []

    columns_copied_from_opponent = (
        [category.column_name for category in rolling_categories]
        + situational_columns
        + core_roster_columns
        + OPPONENT_CONTEXT_STATS
    )
    opponent_columns = [
        team_columns.OPPONENT_PREFIX + column for column in columns_copied_from_opponent
    ]

    return FeatureSet(
        output_column=columns.output_column,
        rolling_categories=rolling_categories,
        situational_stats=situational_stats,
        columns_copied_from_opponent=columns_copied_from_opponent,
        sequence_columns=sorted(set(
            OWN_GAME_STATS
            + ALLOWED_GAME_STATS
            + CONTEXT_COLUMNS
            + [team_columns.OPPONENT_PREFIX + stat for stat in OPPONENT_CONTEXT_STATS]
        )),
        static_columns=sorted(
            set(
                CONTEXT_COLUMNS
                + [category.column_name for category in rolling_categories]
                + situational_columns
                + core_roster_columns
                + opponent_columns
            )
            - set(dropped_static_columns)
        )
    )

# CORE ROSTERS: #
def stored_roster_totals(team_game_data: pd.DataFrame) -> CoreRosterTotals | None:
    """Returns the core roster totals for stored games, or None if the roster columns are turned off."""

    return team_rosters.stored_totals(team_game_data) if READS_CORE_ROSTER else None

def prediction_roster_totals(
    target_game: Game,
    rosters: Mapping[int, RosterScenario]
    ) -> CoreRosterTotals | None:
    """Returns the core roster totals for the game being predicted, or None if the roster columns are turned off."""

    return team_rosters.prediction_totals(target_game, rosters) if READS_CORE_ROSTER else None

# BUILDING THE ROWS: #
def ordered_by_team_and_date(team_game_data: pd.DataFrame) -> pd.DataFrame:
    return team_game_data.sort_values(by=[TEAM_ID, GAME_DATE]).reset_index(drop=True)

def build_rows(
    features: FeatureSet,
    team_game_data: pd.DataFrame,
    roster_totals: CoreRosterTotals | None
    ) -> pd.DataFrame:
    """Adds every feature column to the team game rows. Modifies its input."""

    team_game_data[GAME_DATE] = pd.to_datetime(team_game_data[GAME_DATE])
    team_game_data = ordered_by_team_and_date(team_game_data)

    team_game_data = game_columns.add_points_column(
        team_game_data,
        team_game_store.FIELD_GOALS_MADE.category_name,
        team_game_store.THREE_POINTERS_MADE.category_name,
        team_game_store.FREE_THROWS_MADE.category_name
        )
    team_game_data = game_columns.add_total_rebounds_column(
        team_game_data,
        team_game_store.OFFENSIVE_REBOUNDS.category_name,
        team_game_store.DEFENSIVE_REBOUNDS.category_name
        )
    team_game_data = team_columns.add_possessions_column(
        team_game_data,
        team_game_store.FIELD_GOALS_ATTEMPTED.category_name,
        team_game_store.FREE_THROWS_ATTEMPTED.category_name,
        team_game_store.OFFENSIVE_REBOUNDS.category_name,
        team_game_store.TURNOVERS.category_name
        )
    team_game_data = season_columns.add_encoded_season_type_columns(
        team_game_data,
        GAME_ID,
        team_game_store.SEASON_TYPE.category_name
    )
    team_game_data = team_columns.add_encoded_home_or_away_column(
        team_game_data,
        team_game_store.MATCHUP.category_name
        )
    # Rows with an unknown matchup are not home rows, so they are never used as game samples.
    team_game_data[IS_HOME_ROW] = (
        team_game_data[team_columns.HOME_OR_AWAY].eq(0).fillna(False).astype(bool)
    )
    team_game_data = team_columns.encode_win_loss_column_as_integer(team_game_data, WIN)
    team_game_data[WIN_CATEGORY] = np.where(team_game_data[WIN] == 1, WON, LOST)
    team_game_data = schedule_columns.add_break_columns(
        team_game_data,
        GAME_DATE,
        group_by_column=TEAM_ID
        )
    team_game_data = schedule_columns.add_recent_game_count_columns(
        team_game_data,
        GAME_DATE,
        group_by_column=TEAM_ID
        )
    team_game_data = season_columns.add_season_standings_columns(
        team_game_data,
        GAME_DATE,
        TEAM_ID,
        WIN,
        season_columns.REGULAR_SEASON
        )

    team_game_data = team_columns.add_opponent_stat_columns(
        team_game_data,
        GAME_ID,
        TEAM_ID,
        COPIED_FROM_THE_OTHER_SIDE
        )
    team_game_data = team_columns.add_point_differential_column(
        team_game_data,
        game_columns.POINTS,
        team_columns.OPPONENT_PREFIX + game_columns.POINTS
        )
    team_game_data = team_columns.add_combined_stat_columns(team_game_data, COMBINED_GAME_STATS)

    team_game_data = ordered_by_team_and_date(team_game_data)
    # Rolling columns exclude the current row, so they only use earlier games.
    team_game_data = rolling.add_rolling_function_columns(
        team_game_data,
        features.rolling_categories,
        group_by_column=TEAM_ID
        )

    team_game_data = situations.add_columns(
        team_game_data,
        TEAM_ID,
        SITUATIONS,
        features.situational_stats
        )

    if READS_CORE_ROSTER:
        if roster_totals is None:
            raise ValueError(
                "These rows read who each team has available, so a build has to be given the roster "
                "reading. See feature_engineering/team_rosters.py."
            )

        team_game_data = team_rosters.add_columns(team_game_data, roster_totals)

    team_game_data = team_columns.add_opponent_stat_columns(
        team_game_data,
        GAME_ID,
        TEAM_ID,
        features.columns_copied_from_opponent
        )

    return ordered_by_team_and_date(team_game_data)

def build_histories(
    features: FeatureSet,
    team_game_data: pd.DataFrame,
    roster_totals: CoreRosterTotals | None,
    sample_row_column: str | None = None,
    print_debug: bool = False
    ) -> dict[int, GameHistory]:
    """Builds a GameHistory for each team from the raw team game rows."""

    if print_debug:
        print("Feature engineering team game data...")

    team_game_data = build_rows(features, team_game_data.copy(), roster_totals)
    team_game_data[OUTPUT] = team_game_data[features.output_column]

    if print_debug:
        print("Rearranging data...")

    return split_into_histories(
        team_game_data,
        TEAM_ID,
        GAME_ID,
        GAME_DATE,
        OPPONENT_TEAM_ID,
        features.sequence_columns,
        features.static_columns,
        sample_row_column=sample_row_column
    )

# TARGET GAME: #
def read_history_window(target_game: Game) -> pd.DataFrame:
    started = target_game.date - relativedelta(years=HISTORICAL_WINDOW_LENGTH_YEARS)

    return season_columns.drop_incomplete_game_rows(
        team_game_store.get_game_data_after_date(started),
        team_game_store.SEASON_TYPE.category_name
    )

def find_target_game(
    histories: dict[int, GameHistory],
    team_id: int,
    target_game: Game
    ) -> tuple[GameHistory, int] | None:
    """Returns the team's history and the target game's index, or None if the team has too few past games."""

    history = histories.get(team_id)
    if history is None:
        return None

    found = np.flatnonzero(history.game_ids == placeholders.game_id(target_game))
    if len(found) != 1:
        raise ValueError(
            f"Expected exactly one placeholder game for team {team_id}, found {len(found)}."
        )

    target_index = int(found[0])

    return None if target_index < MINIMUM_PAST_GAMES else (history, target_index)
