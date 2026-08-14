"""
Turning the stored box scores into the inputs a player game statistics model reads.

The same feature build runs for training and for a prediction, so a predicted game is fed through it
as one more row rather than assembled by hand.

A prediction reads that build in two pieces, because only one of them depends on the request. The
games behind the predicted one are the whole league's and the same for every request, so a job builds
them once and every request shares them. See feature_engineering/feature_store.py. The predicted
game's own row is assembled per request, out of the state the player, their team mates and both teams
leave behind, and out of the roster the request named.
"""

from dataclasses import dataclass
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from enum import Enum
from typing import Collection, Iterable

import pandas as pd
import numpy as np

from nba_ml import season
from nba_ml.entities import Game
from nba_ml.feature_engineering import (
    feature_store,
    game_columns,
    placeholders,
    player_columns,
    rolling,
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
    GameHistory,
    SequenceToRead,
    build_inference_sample,
    build_split_samples,
    split_into_histories
)
from nba_ml.machine_learning.datasets import GameSequences, SequenceInputSamples
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.stores import player_games, players, team_games

ROLLING_WINDOW = 15

# How fast the weighted recent form columns forget, in games. Swept against flat windows and beat
# all of them on every stat.
RECENT_FORM_HALFLIFE = 1

# How much history a prediction reads out of the databases.
HISTORICAL_WINDOW_LENGTH_YEARS = 5

BUILD_NAME = "player_stats"
"""Names the directory this family's published whole-league builds are kept under."""

ROSTER_GAMES_READ = player_columns.CORE_ROTATION_WINDOW
"""
How many of the team's last games a prediction reads the whole roster of.

The absent core teammate columns measure the roster of the predicted game against what the team
usually had available over its last CORE_ROTATION_WINDOW games. Every player who appeared in one of
them therefore has to be built alongside the player being predicted, or those columns would total a
thinner team than the one the model was trained on.
"""

# How far back the long window player columns read. A fixed number of games rather than a whole
# career, so a prediction reading only HISTORICAL_WINDOW_LENGTH_YEARS builds what training built.
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

# How many games a player must already have played before one of their games can be a sample. One is
# the floor rather than a choice: the sequence a model reads cannot be empty. A player early in their
# career is kept and GAMES_PLAYED tells the model how little sits behind the averages beside it.
MINIMUM_PAST_GAMES = 1

# TARGET STATS: #
@dataclass(frozen=True)
class TargetStatColumns():
    """
    The columns predicting one stat needs on top of the ones every model gets. Adding a stat to the
    framework means adding one of these and nothing else.
    """

    output_column: str
    """The column holding the value being predicted."""

    sequence_stats: tuple[str, ...] = ()
    """Raw per game columns kept for each game in the window of the player's past games."""

    career_stats: tuple[str, ...] = ()
    """Player stats to carry a long window mean and standard deviation of."""

    player_recent_mean_stats: tuple[str, ...] = ()
    """
    Player stats to carry a recent average of, on top of the box score every model already gets.
    Only derived stats need listing here, since a raw box score column is always covered.
    """

    situational_stats: tuple[str, ...] = ()
    """
    Player stats to read in games like the one being predicted, on top of the always on ones. See
    feature_engineering/situations.py. Each one is given a recent average whether it asked for one or
    not, since that is what a situational reading is measured against.
    """

    opponent_allowed_team_stats: tuple[str, ...] = ()
    """Team stats to measure against the team's own recent average, then average per opponent."""

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

# COMBINING TARGETED STATS: #
DOUBLE_FIGURES = 10
"""What one stat has to reach in a game to count towards a triple double or double double."""

MILESTONE_CATEGORIES = ("stat line reached", "not reached")
"""
What a double figure milestone answers with, most notable first, so a caller drawing the answer leads
with the milestone happening.
"""

MILESTONE_REACHED, MILESTONE_MISSED = range(len(MILESTONE_CATEGORIES))
"""Which position of MILESTONE_CATEGORIES each outcome is, which is the label it is fit against."""

@dataclass(frozen=True)
class StatTotal():
    """The targeted stats added together, which is what a stat line is."""

    def combine(self, stat_values: pd.DataFrame) -> pd.Series:
        return stat_values.sum(axis=1)

    def predicts(self, target_stats: Iterable[TargetStat]) -> tuple[str, ...]:
        return tuple(stat.name.lower().replace("_", " ") for stat in target_stats)

    def describe(self, output_columns: list[str]) -> str:
        return " + ".join(output_columns)

@dataclass(frozen=True)
class DoubleFigureMilestone():
    """
    Whether enough of the targeted stats reached double figures in the same game, which is what a
    double double and a triple double are. The answer is a category rather than a count.
    """

    stats_needed: int
    predicted: str
    """What a reader calls it."""

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
"""
How the stats a model targets become the one value it is fit against.

Adding a way to combine them is one class here holding these three: the label a finished game gets,
the words a reader sees, and a line for the training report. Nothing else branches on which it is.
"""

# Columns every model gets, whatever it is predicting.
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

# A career debut is left out here, because a game only becomes a sample once MINIMUM_PAST_GAMES sit
# behind it, so the game being predicted is never anyone's first.
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

# Minutes are read in every situation, whatever the model predicts, because a player who plays less
# against one team or in one phase of the season does less of everything.
SITUATIONAL_STATS_ALWAYS = [player_games.MINUTES_PLAYED.category_name]

SITUATIONS = list(situations.ALL_SITUATIONS)
"""
Which kinds of game a player's own form is read in. See feature_engineering/situations.py.

All three, unlike the team build, which measured nothing in a team's form against the side it faces.
A player facing one defence again is a likelier thing to matter than a roster facing another roster.
It is still the weakest of the three here, so it is the first to cut if this build is ever trimmed.
"""

TEAM_FRAME_COLUMNS = {
    category.category_name for category in team_games.ALL_CATEGORIES.get_categories()
} | {game_columns.POINTS, game_columns.REBOUNDS, team_columns.POSSESSIONS}
"""
The columns the team frame holds under a name the player frame also uses.

Merging the two suffixes every one of them, so a player column named here is only reachable under
the player suffix afterwards.
"""

# The whole box score, averaged over the player's recent games. This is also what the core teammate
# columns total, so a stat here says what the player brings and what the players around them bring.
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
    """
    Every column name and rolling definition one model needs, resolved once from its target stats.

    Resolving up front means two models can be built at the same time without sharing state, and the
    sample loops read a finished list instead of rebuilding it for every sample.
    """

    output_columns: list[str]
    """The stats the value being predicted is read off."""

    combination: StatCombination
    """How those columns become that one value."""

    player_rolling_categories: list[RollingCategory]

    situational_stats: list[SituationalStat]
    """What a player's form in games like this one is read over. See feature_engineering/situations.py."""

    core_teammate_stat_columns: list[str]
    """Recent player averages to total over the core teammates a team gained, lost and is missing."""

    team_rolling_categories: list[RollingCategory]
    team_difference_columns: list[tuple[str, str]]

    opponent_rolling_categories: list[RollingCategory]
    opponent_columns_to_copy: list[str]
    """The only team columns worth carrying over to the opposing team's row."""

    sequence_columns: list[str]
    """Read for each of the player's past games."""

    static_columns: list[str]
    """Read once, off the game being predicted."""

def _column_name_after_merge(
    player_column: str,
    team_column_names: set[str]
    ) -> str:
    """
    Merging the player and team frames suffixes any column name they both hold, so a player column
    the team frame also has is only reachable under the player suffix afterwards.
    """

    if player_column in team_column_names:
        return player_column + player_columns.PLAYER_SUFFIX

    return player_column

def build_feature_set(
    target_stats: Iterable[TargetStat],
    combination: StatCombination = StatTotal()
    ) -> FeatureSet:
    """
    Resolves the columns a model predicting the given stats needs. Predicting several stats at once
    takes the union of what each one asks for.

    Args:
        combination is how those stats become the one value the model is fit against.
    """

    specifications = [target_stat.value for target_stat in set(target_stats)]

    def gather(always: list[str], selected: list[tuple[str, ...]]) -> list[str]:
        """Merges the always on columns with what each targeted stat asked for, in a stable order."""

        return sorted(set(always).union(*selected))

    career_stats = gather(CAREER_STATS_ALWAYS, [spec.career_stats for spec in specifications])
    situational_stat_names = gather(
        SITUATIONAL_STATS_ALWAYS,
        [spec.situational_stats for spec in specifications]
    )
    # A situational reading is measured against a recent average, so anything read in a situation
    # gets one whether it asked for one or not.
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

    # The same stats again, weighted towards the newest games. The flat window above is slow to
    # notice a player's role changing, and both readings together beat either one alone.
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

    # How the opposing team's own season is going, which is what tells a model whether the game
    # still matters to them. Only their record is carried over, since both teams share the calendar.
    opponent_record_column = team_columns.OPPONENT_PREFIX + season_columns.TEAM_WIN_PERCENTAGE

    # Who the team gained, lost and is missing around the player, measured in the same recent
    # averages the player's own form is measured in.
    core_teammate_stat_columns = [category.column_name for category in player_mean_categories]
    core_teammate_columns = player_columns.get_core_teammate_columns(core_teammate_stat_columns)

    # How much the opponent lets teams beat their own averages is read off the game being predicted
    # and not off each past game. Measured on 2026-08-11: shuffling those ten columns away inside the
    # sequence made the model very slightly better, and leaving them out of it cost nothing.
    sequence_columns = sorted(set(
        SEQUENCE_STATS_ALWAYS
        + [stat for spec in specifications for stat in spec.sequence_stats]
        + [opponent_record_column]
        + core_teammate_columns
    ))

    # The player's own recent average of each targeted stat. Recent form is the strongest single
    # predictor here, and without this the model would have to rebuild it from the raw past games.
    merged_team_columns = (
        {category.column_name for category in team_allowed_mean_categories} | TEAM_FRAME_COLUMNS
    )
    recent_form_columns = [
        _column_name_after_merge(category.column_name, merged_team_columns)
        for category in player_mean_categories + player_weighted_mean_categories
    ]

    # Read off the merged frame, because the player's own games are only reachable there once the
    # team's row is beside them.
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
    """
    Reduces the player information table to one array of numbers per player, in a fixed column order
    so that training and prediction lay the values out the same way.
    """

    features = game_columns.sort_columns_alphabetically(
        player_info.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC, errors='ignore')
    )
    player_ids = player_info[players.PLAYER_ID.category_name].to_numpy()
    values = features.to_numpy(dtype=np.float32)

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
    """
    Returns every game played by a player the databases hold information about, sorted by player and
    then by date so that the grouped columns below read each player's games in the order they
    happened.

    Nobody is dropped for having played too few games. A short career still fills out the teammates
    around the players who have one, and its own games are samples like any other.
    """

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
    """
    Returns every team game with its own rolling state and its opponent's, sorted by team and then
    by date so that the previous game really is the row above.
    """

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
    """
    Turns the raw tables into one finished history per player.

    Every column is either read off the row itself or off the rows in front of it, so a placeholder
    row standing for a game not yet played comes out of this filled the same way a played game does.

    The given frames are not modified, so this can be called more than once on the same data.
    """

    if print_debug:
        print("Feature engineering player info data...")

    player_info = _preprocess_player_info(player_info)

    if print_debug:
        print("Feature engineering player game data...")

    player_game_data = _preprocess_player_game_data(features, player_info, player_game_data.copy())

    if print_debug:
        print("Feature engineering team game data...")

    team_game_data = _preprocess_team_game_data(features, team_game_data.copy())

    # These two read the team's game order, so they come after the team frame is built.
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

    # Last, because it reads the player's finished rolling means and the team's game order.
    player_game_data = player_columns.add_core_teammate_columns(
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

    # After the merge, because what makes a game the same kind of game is on the team's row.
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
    """
    What is stored about every player, which every build reads all of.

    Nobody is left out. Unknown heights and weights are filled with the league's own average, so a
    shorter list would move that average, and a player missing here is dropped from the game data
    entirely, which would leave the core teammate columns totalling a thinner roster. The name is
    dropped because it is held for search and display, and a player without one must not fall out.
    """

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
    """Every team game inside the window, or every one stored where there is no window."""

    team_game_data: pd.DataFrame = (
        team_games.get_all_team_game_data() if window_start_date is None
        else team_games.get_game_data_after_date(window_start_date)
    )

    return season_columns.drop_incomplete_game_rows(
        team_game_data,
        team_games.SEASON_TYPE.category_name
    )

# THE WHOLE LEAGUE: #
def build_league_histories(
        features: FeatureSet,
        window_start_date: date | None = None,
        print_debug: bool = False
    ) -> dict[int, GameHistory]:
    """
    Builds one finished history per player out of everything stored, or out of a window of it.

    This is the expensive half of a prediction and comes out the same for every request, so a job
    runs it once and the service reads what it produced.

    Args:
        window_start_date drops every game played before it. A build over everything stored peaks
        above what the server has, and every window these columns read fits inside a few seasons, so
        the server builds the window it serves and only training reads the whole archive.
    """

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
        validation_split_start_date: datetime,
        test_split_start_date: datetime,
        chunk_step_size: int = 1,
        print_debug: bool = False
        ) -> tuple[
            GameSequences,
            SequenceInputSamples,
            SequenceInputSamples,
            SequenceInputSamples
            ]:
    """
    Builds every labeled sample the league holds, split into training, validation and test by date.

    Returns:
        (games of every player, training samples, validation samples, test samples)
    """

    histories = build_league_histories(features, print_debug=print_debug)

    if print_debug:
        print("Arranging data into training chunks...")

    player_game_sequences, (training, validation, test) = build_split_samples(
        histories,
        (validation_split_start_date, test_split_start_date),
        MINIMUM_PAST_GAMES,
        chunk_step_size,
        training_start_date=training_start_date,
        print_debug=print_debug
    )

    if print_debug:
        print("Finished data processing.")

    return (player_game_sequences, training, validation, test)

# THE GAME BEING PREDICTED: #
@dataclass(frozen=True)
class TargetGameRow():
    """The row standing for the game being predicted, built from the state behind it."""

    static_input: np.ndarray
    """Everything read off the game being predicted, plus the player's own information."""

    opponent_team_id: int
    """Who the player faces, which is what marks those games inside the sequence beside this row."""

def _window_start_date(build: FeatureBuild | None, target_game: Game) -> date | None:
    """
    How far back a prediction reads, and None where it reads everything stored.

    A published build decides it, so the games behind the predicted one and the predicted game's own
    row describe the same stretch of history. Without one, the request reads the years behind the
    game it is about.
    """

    if build is not None:
        return build.window_start_date

    return target_game.date - relativedelta(years=HISTORICAL_WINDOW_LENGTH_YEARS)

def _recent_team_games(
    team_game_data: pd.DataFrame,
    team_id: int,
    before: date
    ) -> pd.DataFrame:
    """
    The team's games before the one being predicted, oldest first.

    Games after it are left out rather than the team's latest game being taken outright, so that a
    game inside recorded history is never built from a roster that only existed later. That reads as
    roster changes that never happened.
    """

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
    removed_core_teammate_player_ids: Collection[int],
    added_core_teammate_player_ids: Collection[int],
    window_start_date: date | None,
    print_debug: bool = False
    ) -> TargetGameRow:
    """
    Builds the one row standing for the game being predicted.

    The row is fed through the same build every played game goes through, so rest, break length and
    every average on it come from the games in front of it rather than from anything assembled by
    hand. That is only the player's real rest while the databases are current, so collect before
    predicting.

    Only what that row reads is built: the player, the team mates whose recent form its roster
    columns total, and both teams. The rest of the league leaves this row untouched, which is what
    makes it the small half of a prediction. The games behind it are the other half, and they are the
    whole league's, so they come from a build every request shares.

    Args:
        removed_core_teammate_player_ids are core players from the team's last game who are out for
        this one. added_core_teammate_player_ids are the reverse, players expected back in. Core
        means the minutes cutoff in player_columns.
        window_start_date is how far back to read, and None reads everything stored. It comes from
        the build the games behind this row came from, so both halves describe the same history.

    Raises:
        PredictionRefused where nothing is stored about the player, or where the team has no earlier
        recorded game to read a roster and a form off.
    """

    if print_debug:
        print("Querying data from databases...")

    # Asked now, so a team that is not playing in this game is refused here rather than part way
    # through a build.
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
    roster_player_ids |= set(added_core_teammate_player_ids)
    roster_player_ids.add(target_player_id)

    player_game_data = season_columns.drop_incomplete_game_rows(
        player_games.get_players_game_data(roster_player_ids, window_start_date),
        player_games.SEASON_TYPE.category_name
    )

    # The target player's whole history is read rather than just the window, because their long
    # window columns are model inputs and a slice of a career would not match what training built.
    # The extra games only feed those columns: a game with no team row drops out when the two merge.
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
        previous_game_player_ids.union(added_core_teammate_player_ids)
        .difference(removed_core_teammate_player_ids)
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
                added_core_teammate_player_ids
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

# THE GAMES BEHIND IT: #
def _read_past_games(
    features: FeatureSet,
    target_player_id: int,
    target_game: Game,
    build: FeatureBuild | None,
    print_debug: bool = False
    ) -> SubjectSequences:
    """
    The player's games behind the one being predicted, in the columns this model reads.

    They come out of the published whole-league build, which holds every column any model of this
    family reads, so one build answers all of them. Where nothing is published, the league is built
    for this request instead, which is what a machine that has never run the build job has. They
    cannot come from a smaller build: what the players around them were doing sits on every one of a
    player's past games, so a build over a handful of players would fill those columns with a thinner
    roster than the real one.

    Raises:
        PredictionRefused where too little sits behind the game for a sequence to be read.
    """

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
    removed_core_teammate_player_ids: Collection[int],
    added_core_teammate_player_ids: Collection[int],
    print_debug: bool = False
    ) -> tuple[GameSequences, SequenceInputSamples]:
    """
    Builds the input for one prediction: the games the player has played, and the single sample that
    reads them.

    The predicted game's row is built first, because it is the cheap half and it holds every reason a
    request cannot be answered from what is stored. See build_target_game_row for what the roster
    arguments mean.
    """

    build = feature_store.current(BUILD_NAME)

    target_row = build_target_game_row(
        features,
        target_player_id,
        target_player_team_id,
        target_game,
        removed_core_teammate_player_ids,
        added_core_teammate_player_ids,
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
