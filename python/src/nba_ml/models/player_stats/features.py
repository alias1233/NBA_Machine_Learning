"""Builds the features and samples for the player stats models from the stored box scores."""

from dataclasses import dataclass
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from enum import Enum
from typing import Iterable

import pandas as pd
import numpy as np

from nba_ml import season
from nba_ml.entities import Game, RosterScenario
from nba_ml.feature_engineering import (
    feature_store,
    game_columns,
    placeholders,
    player_columns,
    rolling,
    roster_columns,
    schedule_columns,
    season_columns,
    situations,
    team_columns
)
from nba_ml.feature_engineering.feature_store import FeatureBuild, SubjectSequences
from nba_ml.feature_engineering.rolling import RollingCategory
from nba_ml.feature_engineering.situations import SituationalStat
from nba_ml.feature_engineering.samples import (
    OUTPUT,
    EvaluationSplit,
    GameHistory,
    SequenceToRead,
    build_inference_sample,
    build_split_samples,
    check_columns_are_finite,
    split_into_histories
)
from nba_ml.machine_learning.datasets import GameSequences, SequenceInputSamples
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.stores import player_games, players, team_games

ROLLING_WINDOW = 15

# Halflife of the exponentially weighted mean columns, in games.
RECENT_FORM_HALFLIFE = 1

# Years of game history loaded for a prediction.
HISTORICAL_WINDOW_LENGTH_YEARS = 5

BUILD_NAME = "player_stats"
"""Name of the directory this family's feature builds are saved in."""

ROSTER_GAMES_READ = roster_columns.CORE_ROTATION_WINDOW
"""Number of the team's last games whose rosters are loaded for a prediction."""

# Window of the career mean and standard deviation columns, in games.
CAREER_WINDOW = 200

PAST_CAREER_MEAN_PREFIX = "PAST_CAREER_MEAN_"
PAST_CAREER_STD_PREFIX = "PAST_CAREER_STD_"
PAST_MEAN_PREFIX = "PAST_MEAN_"
PAST_WEIGHTED_MEAN_PREFIX = "PAST_WEIGHTED_MEAN_"
PAST_MEAN_ALLOWED_INFIX = "PAST_MEAN_ALLOWED_"

PRE_UNUSED_PLAYER_CATEGORIES = [
    player_games.MATCHUP.category_name,
    player_games.WIN_LOSS.category_name,
    player_games.SEASON_TYPE.category_name
]

DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES = [
    player_games.GAME_DATE.category_name
]

POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC = [
    players.PLAYER_ID.category_name,
    players.POSITION.category_name,
    players.FROM_YEAR.category_name,
    players.TO_YEAR.category_name,
    players.BIRTHDATE.category_name
]

# Number of past games a player needs before a game can be used as a sample.
MINIMUM_PAST_GAMES = 1

# TARGET STATS: #
@dataclass(frozen=True)
class TargetStatColumns():
    """The output column for a stat and the extra columns it needs on top of the defaults."""

    output_column: str
    """Column with the value being predicted."""

    sequence_stats: tuple[str, ...] = ()
    """Extra raw stat columns included for each of the player's past games."""

    career_stats: tuple[str, ...] = ()
    """Extra player stats to add a career mean and standard deviation for."""

    player_recent_mean_stats: tuple[str, ...] = ()
    """Extra player stats to add a rolling mean for."""

    situational_stats: tuple[str, ...] = ()
    """Extra player stats to add situational form columns for."""

    opponent_allowed_team_stats: tuple[str, ...] = ()
    """Team stats used for the opponent allowed columns: the stat minus the team's rolling average, averaged per opponent."""

class TargetStat(Enum):
    POINTS = TargetStatColumns(
        output_column=game_columns.POINTS + player_columns.PLAYER_SUFFIX,
        sequence_stats=(
            game_columns.POINTS + player_columns.PLAYER_SUFFIX,
            player_games.OFFENSIVE_REBOUNDS.category_name + player_columns.PLAYER_SUFFIX,
            team_games.ASSISTS.category_name + player_columns.TEAM_SUFFIX,
            player_games.TURNOVERS.category_name + player_columns.PLAYER_SUFFIX,
            player_games.FIELD_GOALS_ATTEMPTED.category_name + player_columns.PLAYER_SUFFIX,
            player_games.FIELD_GOALS_MADE.category_name + player_columns.PLAYER_SUFFIX,
            player_games.THREE_POINTERS_ATTEMPTED.category_name + player_columns.PLAYER_SUFFIX,
            player_games.THREE_POINTERS_MADE.category_name + player_columns.PLAYER_SUFFIX,
            player_games.FREE_THROWS_ATTEMPTED.category_name + player_columns.PLAYER_SUFFIX,
            player_games.FREE_THROWS_MADE.category_name + player_columns.PLAYER_SUFFIX,
        ),
        career_stats=(game_columns.POINTS,),
        player_recent_mean_stats=(game_columns.POINTS,),
        situational_stats=(game_columns.POINTS,),
        opponent_allowed_team_stats=(
            game_columns.POINTS,
            team_games.TURNOVERS.category_name,
            team_games.OFFENSIVE_REBOUNDS.category_name,
            team_games.ASSISTS.category_name,
            team_games.FIELD_GOALS_ATTEMPTED.category_name,
            team_games.FIELD_GOALS_MADE.category_name,
            team_games.THREE_POINTERS_ATTEMPTED.category_name,
            team_games.THREE_POINTERS_MADE.category_name,
            team_games.FREE_THROWS_ATTEMPTED.category_name,
        )
    )

    REBOUNDS = TargetStatColumns(
        output_column=game_columns.REBOUNDS + player_columns.PLAYER_SUFFIX,
        sequence_stats=(
            player_games.OFFENSIVE_REBOUNDS.category_name + player_columns.PLAYER_SUFFIX,
            player_games.DEFENSIVE_REBOUNDS.category_name + player_columns.PLAYER_SUFFIX,
            team_games.FIELD_GOALS_ATTEMPTED.category_name + player_columns.TEAM_SUFFIX,
            team_games.FIELD_GOALS_MADE.category_name + player_columns.TEAM_SUFFIX,
            team_games.THREE_POINTERS_ATTEMPTED.category_name + player_columns.TEAM_SUFFIX,
            team_games.THREE_POINTERS_MADE.category_name + player_columns.TEAM_SUFFIX,
        ),
        career_stats=(
            player_games.OFFENSIVE_REBOUNDS.category_name,
            player_games.DEFENSIVE_REBOUNDS.category_name,
        ),
        player_recent_mean_stats=(game_columns.REBOUNDS,),
        situational_stats=(game_columns.REBOUNDS,),
        opponent_allowed_team_stats=(
            team_games.OFFENSIVE_REBOUNDS.category_name,
            team_games.DEFENSIVE_REBOUNDS.category_name,
            team_games.FIELD_GOALS_ATTEMPTED.category_name,
            team_games.FIELD_GOALS_MADE.category_name,
            team_games.THREE_POINTERS_ATTEMPTED.category_name,
            team_games.THREE_POINTERS_MADE.category_name,
        )
    )

    ASSISTS = TargetStatColumns(
        output_column=player_games.ASSISTS.category_name + player_columns.PLAYER_SUFFIX,
        sequence_stats=(
            player_games.ASSISTS.category_name + player_columns.PLAYER_SUFFIX,
            player_games.TURNOVERS.category_name + player_columns.PLAYER_SUFFIX,
            player_games.FIELD_GOALS_ATTEMPTED.category_name + player_columns.TEAM_SUFFIX,
            player_games.FIELD_GOALS_MADE.category_name + player_columns.TEAM_SUFFIX,
            player_games.THREE_POINTERS_ATTEMPTED.category_name + player_columns.TEAM_SUFFIX,
            player_games.THREE_POINTERS_MADE.category_name + player_columns.TEAM_SUFFIX,
        ),
        career_stats=(player_games.ASSISTS.category_name,),
        situational_stats=(player_games.ASSISTS.category_name,),
        opponent_allowed_team_stats=(
            team_games.ASSISTS.category_name,
            team_games.TURNOVERS.category_name,
            team_games.FIELD_GOALS_ATTEMPTED.category_name,
            team_games.FIELD_GOALS_MADE.category_name,
            team_games.THREE_POINTERS_ATTEMPTED.category_name,
            team_games.THREE_POINTERS_MADE.category_name,
        )
    )

    THREE_POINTERS = TargetStatColumns(
        output_column=player_games.THREE_POINTERS_MADE.category_name + player_columns.PLAYER_SUFFIX,
        sequence_stats=(
            player_games.THREE_POINTERS_MADE.category_name + player_columns.PLAYER_SUFFIX,
            player_games.THREE_POINTERS_ATTEMPTED.category_name + player_columns.PLAYER_SUFFIX,
            player_games.FIELD_GOALS_ATTEMPTED.category_name + player_columns.PLAYER_SUFFIX,
            team_games.THREE_POINTERS_ATTEMPTED.category_name + player_columns.TEAM_SUFFIX,
            team_games.THREE_POINTERS_MADE.category_name + player_columns.TEAM_SUFFIX,
            team_games.FIELD_GOALS_ATTEMPTED.category_name + player_columns.TEAM_SUFFIX,
        ),
        career_stats=(player_games.THREE_POINTERS_MADE.category_name,),
        situational_stats=(player_games.THREE_POINTERS_MADE.category_name,),
        opponent_allowed_team_stats=(
            team_games.THREE_POINTERS_ATTEMPTED.category_name,
            team_games.THREE_POINTERS_MADE.category_name,
            team_games.FIELD_GOALS_ATTEMPTED.category_name,
            game_columns.POINTS,
        )
    )

    STEALS = TargetStatColumns(
        output_column=player_games.STEALS.category_name + player_columns.PLAYER_SUFFIX,
        sequence_stats=(
            player_games.STEALS.category_name + player_columns.PLAYER_SUFFIX,
            player_games.DEFENSIVE_REBOUNDS.category_name + player_columns.PLAYER_SUFFIX,
            team_games.STEALS.category_name + player_columns.TEAM_SUFFIX,
            team_games.TURNOVERS.category_name + player_columns.TEAM_SUFFIX,
        ),
        career_stats=(player_games.STEALS.category_name,),
        situational_stats=(player_games.STEALS.category_name,),
        opponent_allowed_team_stats=(
            team_games.STEALS.category_name,
            team_games.TURNOVERS.category_name,
        )
    )

    BLOCKS = TargetStatColumns(
        output_column=player_games.BLOCKS.category_name + player_columns.PLAYER_SUFFIX,
        sequence_stats=(
            player_games.BLOCKS.category_name + player_columns.PLAYER_SUFFIX,
            player_games.DEFENSIVE_REBOUNDS.category_name + player_columns.PLAYER_SUFFIX,
            team_games.BLOCKS.category_name + player_columns.TEAM_SUFFIX,
        ),
        career_stats=(player_games.BLOCKS.category_name,),
        situational_stats=(player_games.BLOCKS.category_name,),
        opponent_allowed_team_stats=(
            team_games.BLOCKS.category_name,
            team_games.FIELD_GOALS_ATTEMPTED.category_name,
        )
    )

    TURNOVERS = TargetStatColumns(
        output_column=player_games.TURNOVERS.category_name + player_columns.PLAYER_SUFFIX,
        sequence_stats=(
            player_games.TURNOVERS.category_name + player_columns.PLAYER_SUFFIX,
            player_games.ASSISTS.category_name + player_columns.PLAYER_SUFFIX,
            player_games.FIELD_GOALS_ATTEMPTED.category_name + player_columns.PLAYER_SUFFIX,
            team_games.TURNOVERS.category_name + player_columns.TEAM_SUFFIX,
        ),
        career_stats=(player_games.TURNOVERS.category_name,),
        situational_stats=(player_games.TURNOVERS.category_name,),
        opponent_allowed_team_stats=(
            team_games.TURNOVERS.category_name,
            team_games.STEALS.category_name,
        )
    )

# STAT COMBINATIONS: #
DOUBLE_FIGURES = 10
"""Value a stat must reach to count towards a double-double or triple-double."""

MILESTONE_CATEGORIES = ("stat line reached", "not reached")
"""Output categories of the double-double and triple-double models."""

MILESTONE_REACHED, MILESTONE_MISSED = range(len(MILESTONE_CATEGORIES))
"""Class index of each outcome in MILESTONE_CATEGORIES."""

@dataclass(frozen=True)
class StatTotal():
    """Combines the target stats by adding them together."""

    def combine(self, stat_values: pd.DataFrame) -> pd.Series:
        return stat_values.sum(axis=1)

    def predicts(self, target_stats: Iterable[TargetStat]) -> tuple[str, ...]:
        return tuple(stat.name.lower().replace("_", " ") for stat in target_stats)

    def describe(self, output_columns: list[str]) -> str:
        return " + ".join(output_columns)

@dataclass(frozen=True)
class DoubleFigureMilestone():
    """Combines the target stats into whether enough of them reached double figures in a game."""

    stats_needed: int
    predicted: str
    """Display name of the predicted value."""

    def combine(self, stat_values: pd.DataFrame) -> pd.Series:
        reached = (stat_values >= DOUBLE_FIGURES).sum(axis=1) >= self.stats_needed

        return pd.Series(
            np.where(reached, MILESTONE_REACHED, MILESTONE_MISSED),
            index=stat_values.index
        )

    def predicts(self, target_stats: Iterable[TargetStat]) -> tuple[str, ...]:
        return (self.predicted,)

    def describe(self, output_columns: list[str]) -> str:
        return f"{self.stats_needed} or more of {', '.join(output_columns)} reaching {DOUBLE_FIGURES}"

StatCombination = StatTotal | DoubleFigureMilestone
"""The ways a model's target stats can be combined into the value it predicts."""

# Columns every model uses, regardless of its target.
SEQUENCE_STATS_ALWAYS = [
    player_games.MINUTES_PLAYED.category_name + player_columns.PLAYER_SUFFIX,
    game_columns.POINTS + player_columns.TEAM_SUFFIX,
    team_columns.OPPONENT_PREFIX + game_columns.POINTS,
    player_games.PLUS_MINUS.category_name,
    player_games.PERSONAL_FOULS.category_name + player_columns.PLAYER_SUFFIX,
    team_columns.HOME_OR_AWAY, schedule_columns.REST, schedule_columns.BREAK_LENGTH,
    schedule_columns.SEASON_OPENER, schedule_columns.CAREER_DEBUT,
    player_columns.CHANGED_TEAM,
    team_columns.POSSESSIONS,
    team_games.MINUTES_PLAYED.category_name + player_columns.TEAM_SUFFIX
] + (
    season_columns.ALL_SEASON_TYPES
    + season_columns.ALL_SEASON_CONTEXT_COLUMNS
    + player_columns.ALL_AVAILABILITY_COLUMNS
    + schedule_columns.get_recent_game_count_columns()
)

STATIC_STATS_ALWAYS = [
    player_columns.NBA_EXPERIENCE_DURING_GAME,
    team_columns.HOME_OR_AWAY, schedule_columns.REST, schedule_columns.BREAK_LENGTH,
    schedule_columns.SEASON_OPENER,
    player_columns.CHANGED_TEAM,
    schedule_columns.GAMES_PLAYED
] + (
    season_columns.ALL_SEASON_TYPES
    + season_columns.ALL_SEASON_CONTEXT_COLUMNS
    + player_columns.ALL_AVAILABILITY_COLUMNS
    + schedule_columns.get_recent_game_count_columns()
)

OPPONENT_ALLOWED_TEAM_STATS_ALWAYS = [
    team_games.PERSONAL_FOULS.category_name
]
CAREER_STATS_ALWAYS: list[str] = []

SITUATIONAL_STATS_ALWAYS = [player_games.MINUTES_PLAYED.category_name]

SITUATIONS = list(situations.ALL_SITUATIONS)
"""Situations that player form is tracked for."""

TEAM_FRAME_COLUMNS = {
    category.category_name for category in team_games.ALL_CATEGORIES.get_categories()
} | {game_columns.POINTS, game_columns.REBOUNDS, team_columns.POSSESSIONS}
"""Team dataframe columns whose names can also appear in the player dataframe."""

# Box score stats that always get a rolling mean.
PLAYER_RECENT_MEAN_STATS_ALWAYS = [
    player_games.MINUTES_PLAYED.category_name,
    player_games.FIELD_GOALS_ATTEMPTED.category_name,
    player_games.FIELD_GOALS_MADE.category_name,
    player_games.THREE_POINTERS_ATTEMPTED.category_name,
    player_games.THREE_POINTERS_MADE.category_name,
    player_games.FREE_THROWS_ATTEMPTED.category_name,
    player_games.FREE_THROWS_MADE.category_name,
    player_games.OFFENSIVE_REBOUNDS.category_name,
    player_games.DEFENSIVE_REBOUNDS.category_name,
    player_games.ASSISTS.category_name,
    player_games.TURNOVERS.category_name,
    player_games.STEALS.category_name,
    player_games.BLOCKS.category_name,
    player_games.PERSONAL_FOULS.category_name
]

@dataclass(frozen=True)
class FeatureSet():
    """The columns and rolling definitions used by one model."""

    output_columns: list[str]
    """Columns of the stats that make up the predicted value."""

    combination: StatCombination
    """The method used to combine those columns into the predicted value."""

    player_rolling_categories: list[RollingCategory]

    situational_stats: list[SituationalStat]
    """Stats the situational form columns are built for."""

    core_teammate_stat_columns: list[str]
    """Player rolling mean columns summed over the core teammates a team gained, lost and is missing."""

    team_rolling_categories: list[RollingCategory]
    team_difference_columns: list[tuple[str, str]]

    opponent_rolling_categories: list[RollingCategory]
    opponent_columns_to_copy: list[str]
    """Team columns copied onto the opponent's row."""

    sequence_columns: list[str]
    """Columns taken from each of the player's past games."""

    static_columns: list[str]
    """Columns taken from the game being predicted."""

def _column_name_after_merge(
    player_column: str,
    team_column_names: set[str]
    ) -> str:
    """Returns the column's name after the merge. Player columns that clash with a team column get the player suffix."""

    if player_column in team_column_names:
        return player_column + player_columns.PLAYER_SUFFIX

    return player_column

def build_feature_set(
    target_stats: Iterable[TargetStat],
    combination: StatCombination = StatTotal()
    ) -> FeatureSet:
    """Returns the feature set for a model predicting the given stats."""

    specifications = [target_stat.value for target_stat in set(target_stats)]

    def gather(always: list[str], selected: list[tuple[str, ...]]) -> list[str]:
        """Merges the default columns with the ones each target stat adds, sorted by name."""

        return sorted(set(always).union(*selected))

    career_stats = gather(CAREER_STATS_ALWAYS, [spec.career_stats for spec in specifications])
    situational_stat_names = gather(
        SITUATIONAL_STATS_ALWAYS,
        [spec.situational_stats for spec in specifications]
    )
    player_recent_mean_stats = gather(
        PLAYER_RECENT_MEAN_STATS_ALWAYS + situational_stat_names,
        [spec.player_recent_mean_stats for spec in specifications]
    )
    opponent_allowed_team_stats = gather(
        OPPONENT_ALLOWED_TEAM_STATS_ALWAYS,
        [spec.opponent_allowed_team_stats for spec in specifications]
    )

    def rolling_means(stats: list[str], max_window_length: int) -> list[RollingCategory]:
        return [
            RollingCategory(PAST_MEAN_PREFIX + stat, stat, rolling.MEAN_FUNCTION, max_window_length)
            for stat in stats
        ]

    career_categories = [
        RollingCategory(PAST_CAREER_MEAN_PREFIX + stat, stat, rolling.MEAN_FUNCTION, CAREER_WINDOW)
        for stat in career_stats
    ] + [
        RollingCategory(PAST_CAREER_STD_PREFIX + stat, stat, rolling.STD_FUNCTION, CAREER_WINDOW)
        for stat in career_stats
    ]
    player_mean_categories = rolling_means(player_recent_mean_stats, ROLLING_WINDOW)
    team_allowed_mean_categories = rolling_means(opponent_allowed_team_stats, ROLLING_WINDOW)

    # The same stats again as exponentially weighted means.
    player_weighted_mean_categories = [
        RollingCategory(
            PAST_WEIGHTED_MEAN_PREFIX + stat,
            stat,
            rolling.MEAN_FUNCTION,
            halflife=RECENT_FORM_HALFLIFE
        )
        for stat in player_recent_mean_stats
    ]

    team_difference_columns = [(stat, PAST_MEAN_PREFIX + stat) for stat in opponent_allowed_team_stats]
    team_stats_over_mean_columns = game_columns.get_all_differences_columns(team_difference_columns)

    opponent_allowed_team_categories = [
        RollingCategory(
            team_columns.OPPONENT_PREFIX + PAST_MEAN_ALLOWED_INFIX + stat,
            stat,
            rolling.MEAN_FUNCTION,
            ROLLING_WINDOW
        ) for stat in team_stats_over_mean_columns
    ]

    opponent_record_column = team_columns.OPPONENT_PREFIX + season_columns.TEAM_WIN_PERCENTAGE

    core_teammate_stat_columns = [category.column_name for category in player_mean_categories]
    core_teammate_columns = roster_columns.core_roster_columns(core_teammate_stat_columns)

    sequence_columns = sorted(set(
        SEQUENCE_STATS_ALWAYS
        + [stat for spec in specifications for stat in spec.sequence_stats]
        + [opponent_record_column]
        + core_teammate_columns
    ))

    merged_team_columns = (
        {category.column_name for category in team_allowed_mean_categories} | TEAM_FRAME_COLUMNS
    )
    recent_form_columns = [
        _column_name_after_merge(category.column_name, merged_team_columns)
        for category in player_mean_categories + player_weighted_mean_categories
    ]

    situational_stats = [
        SituationalStat(
            stat,
            _column_name_after_merge(stat, merged_team_columns),
            _column_name_after_merge(PAST_MEAN_PREFIX + stat, merged_team_columns)
        )
        for stat in situational_stat_names
    ]
    situational_columns = situations.all_columns(SITUATIONS, situational_stats)

    static_columns = sorted(set(
        STATIC_STATS_ALWAYS
        + [category.column_name for category in career_categories]
        + [category.column_name for category in opponent_allowed_team_categories]
        + [opponent_record_column]
        + recent_form_columns
        + situational_columns
        + core_teammate_columns
    ))

    return FeatureSet(
        output_columns=sorted({spec.output_column for spec in specifications}),
        combination=combination,
        player_rolling_categories=career_categories + player_mean_categories + player_weighted_mean_categories,
        situational_stats=situational_stats,
        core_teammate_stat_columns=core_teammate_stat_columns,
        team_rolling_categories=team_allowed_mean_categories,
        team_difference_columns=team_difference_columns,
        opponent_rolling_categories=opponent_allowed_team_categories,
        opponent_columns_to_copy=[
            team_games.TEAM_ID.category_name,
            game_columns.POINTS,
            season_columns.TEAM_WIN_PERCENTAGE
        ],
        sequence_columns=sequence_columns,
        static_columns=static_columns
    )

# PREPROCESSED DATA: #
def _build_player_info_features(
    player_info: pd.DataFrame
    ) -> dict[int, np.ndarray]:
    """Converts the player info table to one array per player, with columns in alphabetical order."""

    features = game_columns.sort_columns_alphabetically(
        player_info.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC, errors='ignore')
    )
    player_ids = player_info[players.PLAYER_ID.category_name].to_numpy()
    values = features.to_numpy(dtype=np.float32)

    check_columns_are_finite(values, list(features.columns), "player information columns")

    return {int(player_id): values[position] for position, player_id in enumerate(player_ids)}

def _preprocess_player_info(player_info: pd.DataFrame) -> pd.DataFrame:
    player_info = player_info.copy()

    player_info[players.FROM_YEAR.category_name] = pd.to_datetime(
        player_info[players.FROM_YEAR.category_name], format='%Y'
        )
    player_info = player_columns.convert_height_to_inches(
        player_info,
        players.HEIGHT.category_name,
        fill_unknown_with_mean=True
    )
    player_info = player_columns.encode_undrafted(
        player_info,
        players.DRAFT_NUMBER.category_name
    )
    player_info = player_columns.handle_unknown_weight(
        player_info,
        players.WEIGHT.category_name,
        fill_unknown_with_mean=True
    )

    return player_info

def _preprocess_player_game_data(
    features: FeatureSet,
    player_info: pd.DataFrame,
    player_game_data: pd.DataFrame
    ) -> pd.DataFrame:
    """Returns every game of every known player, sorted by player and then by date."""

    player_game_data = player_game_data.drop(columns=PRE_UNUSED_PLAYER_CATEGORIES, errors='ignore')
    player_game_data[player_games.GAME_DATE.category_name] = pd.to_datetime(
        player_game_data[player_games.GAME_DATE.category_name]
        )
    player_game_data = game_columns.add_points_column(
        player_game_data,
        player_games.FIELD_GOALS_MADE.category_name,
        player_games.THREE_POINTERS_MADE.category_name,
        player_games.FREE_THROWS_MADE.category_name
        )
    player_game_data = game_columns.add_total_rebounds_column(
        player_game_data,
        player_games.OFFENSIVE_REBOUNDS.category_name,
        player_games.DEFENSIVE_REBOUNDS.category_name
        )
    player_game_data = player_columns.add_years_NBA_experience_during_game_column(
        player_game_data,
        player_info,
        players.PLAYER_ID.category_name,
        player_games.PLAYER_ID.category_name,
        players.FROM_YEAR.category_name,
        player_games.GAME_DATE.category_name
    )

    player_id = player_game_data[player_games.PLAYER_ID.category_name]
    player_game_data = player_game_data[
        player_id.isin(player_info[players.PLAYER_ID.category_name])
    ]
    player_game_data = player_game_data.sort_values(
        by=[player_games.PLAYER_ID.category_name, player_games.GAME_DATE.category_name]
        ).reset_index(drop=True)

    player_game_data = schedule_columns.add_break_columns(
        player_game_data,
        player_games.GAME_DATE.category_name,
        group_by_column=player_games.PLAYER_ID.category_name
        )
    player_game_data = player_columns.add_changed_team_column(
        player_game_data,
        player_games.TEAM_ID.category_name,
        group_by_column=player_games.PLAYER_ID.category_name
    )
    player_game_data = schedule_columns.add_games_played_column(
        player_game_data,
        player_games.PLAYER_ID.category_name
    )
    player_game_data = schedule_columns.add_recent_game_count_columns(
        player_game_data,
        player_games.GAME_DATE.category_name,
        group_by_column=player_games.PLAYER_ID.category_name
    )
    return rolling.add_rolling_function_columns(
        player_game_data,
        features.player_rolling_categories,
        group_by_column=player_games.PLAYER_ID.category_name
    )

def _preprocess_team_game_data(
    features: FeatureSet,
    team_game_data: pd.DataFrame
    ) -> pd.DataFrame:
    """Returns every team game with its rolling columns, sorted by team and then by date."""

    team_game_data[team_games.GAME_DATE.category_name] = pd.to_datetime(
        team_game_data[team_games.GAME_DATE.category_name]
        )
    team_game_data = team_game_data.sort_values(
        by=[team_games.TEAM_ID.category_name, team_games.GAME_DATE.category_name]
        ).reset_index(drop=True)

    team_game_data = game_columns.add_points_column(
        team_game_data,
        team_games.FIELD_GOALS_MADE.category_name,
        team_games.THREE_POINTERS_MADE.category_name,
        team_games.FREE_THROWS_MADE.category_name
        )
    team_game_data = game_columns.add_total_rebounds_column(
        team_game_data,
        team_games.OFFENSIVE_REBOUNDS.category_name,
        team_games.DEFENSIVE_REBOUNDS.category_name
        )
    team_game_data = team_columns.add_possessions_column(
        team_game_data,
        team_games.FIELD_GOALS_ATTEMPTED.category_name,
        team_games.FREE_THROWS_ATTEMPTED.category_name,
        team_games.OFFENSIVE_REBOUNDS.category_name,
        team_games.TURNOVERS.category_name
        )
    team_game_data = season_columns.add_encoded_season_type_columns(
        team_game_data,
        team_games.GAME_ID.category_name,
        team_games.SEASON_TYPE.category_name
        )
    team_game_data = team_columns.add_encoded_home_or_away_column(
        team_game_data,
        team_games.MATCHUP.category_name
        )
    team_game_data = team_columns.encode_win_loss_column_as_integer(
        team_game_data,
        team_games.WIN_LOSS.category_name
    )
    team_game_data = season_columns.add_season_standings_columns(
        team_game_data,
        team_games.GAME_DATE.category_name,
        team_games.TEAM_ID.category_name,
        team_games.WIN_LOSS.category_name,
        season_columns.REGULAR_SEASON
    )

    team_game_data = rolling.add_rolling_function_columns(
        team_game_data,
        features.team_rolling_categories,
        group_by_column=team_games.TEAM_ID.category_name
    )
    team_game_data = team_columns.add_opponent_stat_columns(
        team_game_data,
        team_games.GAME_ID.category_name,
        team_games.TEAM_ID.category_name,
        features.opponent_columns_to_copy
        )
    team_game_data = game_columns.add_differences_columns(
        team_game_data,
        features.team_difference_columns
    )

    opponent_team_id_column = team_columns.OPPONENT_PREFIX + team_games.TEAM_ID.category_name
    team_game_data = team_game_data.sort_values(
        by=[opponent_team_id_column, team_games.GAME_DATE.category_name]
        ).reset_index(drop=True)

    return rolling.add_rolling_function_columns(
        team_game_data,
        features.opponent_rolling_categories,
        group_by_column=opponent_team_id_column
    )

def build_histories(
        features: FeatureSet,
        player_info: pd.DataFrame,
        player_game_data: pd.DataFrame,
        team_game_data: pd.DataFrame,
        print_debug: bool = False
        ) -> dict[int, GameHistory]:
    """Builds a GameHistory for each player from the raw tables."""

    if print_debug:
        print("Feature engineering player info data...")

    player_info = _preprocess_player_info(player_info)

    if print_debug:
        print("Feature engineering player game data...")

    player_game_data = _preprocess_player_game_data(features, player_info, player_game_data.copy())

    if print_debug:
        print("Feature engineering team game data...")

    team_game_data = _preprocess_team_game_data(features, team_game_data.copy())

    # These columns need the team's game order, so they are added after the team data is built.
    player_game_data = player_columns.add_availability_columns(
        player_game_data,
        team_game_data,
        player_games.PLAYER_ID.category_name,
        player_games.GAME_ID.category_name,
        player_games.TEAM_ID.category_name,
        team_games.GAME_ID.category_name,
        team_games.TEAM_ID.category_name,
        team_games.GAME_DATE.category_name
    )

    # Added last because it needs the player's rolling means and the team's game order.
    player_game_data = roster_columns.add_core_teammate_columns(
        player_game_data,
        roster_columns.core_roster_totals(
            player_game_data,
            team_game_data,
            player_games.PLAYER_ID.category_name,
            player_games.GAME_ID.category_name,
            player_games.TEAM_ID.category_name,
            player_games.MINUTES_PLAYED.category_name,
            PAST_MEAN_PREFIX + player_games.MINUTES_PLAYED.category_name,
            team_games.GAME_ID.category_name,
            team_games.TEAM_ID.category_name,
            team_games.GAME_DATE.category_name,
            features.core_teammate_stat_columns
        ),
        player_games.PLAYER_ID.category_name,
        player_games.GAME_ID.category_name,
        player_games.TEAM_ID.category_name,
        features.core_teammate_stat_columns
    )

    if print_debug:
        print("Rearranging data...")

    player_team_game_data = player_columns.merge_player_team_game_data(
        player_game_data,
        team_game_data,
        team_games.GAME_ID.category_name,
        player_games.GAME_ID.category_name,
        team_games.TEAM_ID.category_name,
        player_games.TEAM_ID.category_name,
        DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES
    )
    player_team_game_data = player_team_game_data.sort_values(
        by=[player_games.PLAYER_ID.category_name, team_games.GAME_DATE.category_name]
        ).reset_index(drop=True)

    # Added after the merge because the situation columns are on the team's row.
    player_team_game_data = situations.add_columns(
        player_team_game_data,
        player_games.PLAYER_ID.category_name,
        SITUATIONS,
        features.situational_stats
    )

    player_team_game_data[OUTPUT] = features.combination.combine(
        player_team_game_data[features.output_columns]
    )

    histories = split_into_histories(
        player_team_game_data,
        player_games.PLAYER_ID.category_name,
        team_games.GAME_ID.category_name,
        team_games.GAME_DATE.category_name,
        team_columns.OPPONENT_PREFIX + team_games.TEAM_ID.category_name,
        features.sequence_columns,
        features.static_columns,
        _build_player_info_features(player_info)
    )

    if print_debug:
        print("Finished generating game data.")

    return histories

def _read_player_info() -> pd.DataFrame:
    """Returns the stored player info, without names and without rows missing a first season."""

    player_info: pd.DataFrame = players.get_all_players_info().drop(
        columns=[players.PLAYER_NAME.category_name]
    )

    player_info = player_info.dropna(subset=[
        players.PLAYER_ID.category_name,
        players.FROM_YEAR.category_name
    ])

    if player_info.empty:
        raise ValueError("No usable player information is stored. Run nba-collect all before training a player statistic model.")

    return player_info

def _read_team_games(window_start_date: date | None) -> pd.DataFrame:
    """Returns the complete team games from window_start_date onwards, or all of them if it is None."""

    team_game_data: pd.DataFrame = (
        team_games.get_all_team_game_data() if window_start_date is None
        else team_games.get_game_data_after_date(window_start_date)
    )

    return season_columns.drop_incomplete_game_rows(
        team_game_data,
        team_games.SEASON_TYPE.category_name
    )

# ALL PLAYERS: #
def build_league_histories(
        features: FeatureSet,
        window_start_date: date | None = None,
        print_debug: bool = False
    ) -> dict[int, GameHistory]:
    """Builds a GameHistory for every player from the stored games, optionally from window_start_date onwards."""

    if print_debug:
        print("Querying data from databases...")

    all_player_game_data: pd.DataFrame = (
        player_games.get_all_player_game_data() if window_start_date is None
        else player_games.get_game_data_after_date(window_start_date)
    )

    return build_histories(
        features,
        _read_player_info(),
        season_columns.drop_incomplete_game_rows(
            all_player_game_data,
            player_games.SEASON_TYPE.category_name
        ),
        _read_team_games(window_start_date),
        print_debug
    )

# TRAINING DATA: #
def get_all_labeled_data(
        features: FeatureSet,
        training_start_date: datetime,
        evaluation_split: EvaluationSplit,
        chunk_step_size: int = 1,
        print_debug: bool = False
        ) -> tuple[
            GameSequences,
            SequenceInputSamples,
            SequenceInputSamples,
            SequenceInputSamples
            ]:
    """Builds every labeled sample, split into training, validation and test."""

    histories = build_league_histories(features, print_debug=print_debug)

    if print_debug:
        print("Arranging data into training chunks...")

    player_game_sequences, (training, validation, test) = build_split_samples(
        histories,
        evaluation_split,
        MINIMUM_PAST_GAMES,
        chunk_step_size,
        sequence_columns=features.sequence_columns,
        static_columns=features.static_columns,
        training_start_date=training_start_date,
        print_debug=print_debug
    )

    if print_debug:
        print("Finished data processing.")

    return (player_game_sequences, training, validation, test)

# TARGET GAME: #
@dataclass(frozen=True)
class TargetGameRow():
    """The model inputs taken from the game being predicted."""

    static_input: np.ndarray
    """The static columns of the game being predicted, plus the player info features."""

    opponent_team_id: int
    """ID of the team the player is facing."""

def _window_start_date(build: FeatureBuild | None, target_game: Game) -> date | None:
    """Returns the earliest game date a prediction uses. None means every stored game."""

    if build is not None:
        return build.window_start_date

    return target_game.date - relativedelta(years=HISTORICAL_WINDOW_LENGTH_YEARS)

def _recent_team_games(
    team_game_data: pd.DataFrame,
    team_id: int,
    before: date
    ) -> pd.DataFrame:
    """Returns the team's games before the given date, oldest first."""

    played = team_game_data[
        (team_game_data[team_games.TEAM_ID.category_name] == team_id)
        & (team_game_data[team_games.GAME_DATE.category_name] < season.to_date_string(before))
    ]

    return played.sort_values(by=team_games.GAME_DATE.category_name)

def build_target_game_row(
    features: FeatureSet,
    target_player_id: int,
    target_player_team_id: int,
    target_game: Game,
    scenario: RosterScenario,
    window_start_date: date | None,
    print_debug: bool = False
    ) -> TargetGameRow:
    """Builds the model inputs for the game being predicted."""

    if print_debug:
        print("Querying data from databases...")

    # Raises if the team is not playing in this game.
    target_game.opponent_of(target_player_team_id)

    player_info = _read_player_info()

    if target_player_id not in player_info[players.PLAYER_ID.category_name].values:
        raise PredictionRefused(
            Refusal.MISSING_PLAYER_INFORMATION,
            f"Nothing is stored about player {target_player_id} themselves, which every model reads."
        )

    team_game_data = _read_team_games(window_start_date)
    recent_team_games = _recent_team_games(team_game_data, target_player_team_id, target_game.date)

    if recent_team_games.empty:
        raise PredictionRefused(
            Refusal.NO_TEAM_HISTORY,
            f"Team {target_player_team_id} has no recorded game before {season.to_date_string(target_game.date)}."
        )

    if print_debug:
        print("Reading the roster around the player...")

    recent_game_ids = recent_team_games[team_games.GAME_ID.category_name]
    roster_player_ids = player_games.player_ids_in_games(
        target_player_team_id,
        recent_game_ids.tail(ROSTER_GAMES_READ).tolist()
    )
    roster_player_ids |= set(scenario.returning)
    roster_player_ids.add(target_player_id)

    player_game_data = season_columns.drop_incomplete_game_rows(
        player_games.get_players_game_data(roster_player_ids, window_start_date),
        player_games.SEASON_TYPE.category_name
    )

    # Load the target player's full history, since their career columns need it.
    target_player_game_data = season_columns.drop_incomplete_game_rows(
        player_games.get_specific_player_game_data(target_player_id),
        player_games.SEASON_TYPE.category_name
    )
    player_game_data = pd.concat([player_game_data, target_player_game_data]).drop_duplicates(
        subset=[player_games.PLAYER_ID.category_name, player_games.GAME_ID.category_name]
    )

    previous_game_player_ids = set(
        player_game_data[
            (player_game_data[player_games.TEAM_ID.category_name] == target_player_team_id)
            & (player_game_data[player_games.GAME_ID.category_name] == recent_game_ids.iloc[-1])
        ][player_games.PLAYER_ID.category_name]
    )
    playing_player_ids = (
        previous_game_player_ids.union(scenario.returning).difference(scenario.without)
    )
    playing_player_ids.add(target_player_id)

    if print_debug:
        print("Creating placeholder rows...")

    player_game_data = pd.concat(
        [
            player_game_data,
            placeholders.player_rows(
                target_game,
                target_player_team_id,
                playing_player_ids,
                scenario.returning
            )
        ],
        ignore_index=True
    )
    team_game_data = pd.concat(
        [
            team_game_data,
            placeholders.game_rows(target_game)
        ],
        ignore_index=True
    )

    if print_debug:
        print("Processing data...")

    histories = build_histories(features, player_info, player_game_data, team_game_data)
    history = histories.get(target_player_id)

    if history is None:
        raise ValueError(f"The feature build produced no games for player {target_player_id}.")

    found = np.flatnonzero(history.game_ids == placeholders.game_id(target_game))

    if len(found) != 1:
        raise ValueError(
            f"Expected exactly one placeholder game for player {target_player_id}, found {len(found)}."
        )

    target_index = int(found[0])

    return TargetGameRow(
        history.static_input(target_index),
        int(history.opponent_team_ids[target_index])
    )

# PAST GAMES: #
def _read_past_games(
    features: FeatureSet,
    target_player_id: int,
    target_game: Game,
    build: FeatureBuild | None,
    print_debug: bool = False
    ) -> SubjectSequences:
    """Returns the player's games before the target game, with the columns this model uses."""

    if build is None:
        history = build_league_histories(
            features,
            _window_start_date(None, target_game),
            print_debug
        ).get(target_player_id)
        held = None if history is None else feature_store.sequences_in(history)

    else:
        found = build.subjects.get(target_player_id)
        held = None if found is None else found.with_columns(
            build.column_positions(features.sequence_columns)
        )

    games = (
        feature_store.no_games(len(features.sequence_columns)) if held is None
        else held.before(target_game.date)
    )

    if games.game_count < MINIMUM_PAST_GAMES:
        raise PredictionRefused(
            Refusal.TOO_FEW_GAMES,
            f"The build found {games.game_count} games for player {target_player_id} before "
            f"{season.to_date_string(target_game.date)}, and a prediction reads at least "
            f"{MINIMUM_PAST_GAMES}."
        )

    return games

def get_inference_data(
    features: FeatureSet,
    target_player_id: int,
    target_player_team_id: int,
    target_game: Game,
    scenario: RosterScenario,
    print_debug: bool = False
    ) -> tuple[GameSequences, SequenceInputSamples]:
    """Builds the input for one prediction from the player's past games and the target game row."""

    build = feature_store.current(BUILD_NAME)

    target_row = build_target_game_row(
        features,
        target_player_id,
        target_player_team_id,
        target_game,
        scenario,
        _window_start_date(build, target_game),
        print_debug
    )
    past_games = _read_past_games(features, target_player_id, target_game, build, print_debug)

    if print_debug:
        print("Creating input chunk...")

    return build_inference_sample(
        [
            SequenceToRead(
                past_games.sequence_values,
                past_games.opponent_team_ids,
                target_row.opponent_team_id
            )
        ],
        target_row.static_input
    )
