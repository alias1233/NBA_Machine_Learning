"""
Turning the stored team box scores into one engineered row per team per game.

A stored row is one team's line in one game. This adds everything that can be worked out about that
row before the game is played: what the team and the side it faces had been doing, and where the game
sits in the schedule and in the season. What it never adds is anything the game itself decided.

Two families read these rows. Team statistics asks about one named team, and game statistics asks
about the whole game. They cut the rows into samples differently, so that part is theirs, but the
rows themselves and the columns on them are the same, so they are here.

Every rolling column leaves its own row out, so a row only ever holds what was known before it. That
is what lets a game not yet played be fed through the same build as one already played.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from nba_ml.entities import Game
from nba_ml.feature_engineering import (
    game_columns,
    placeholders,
    rolling,
    schedule_columns,
    season_columns,
    situations,
    team_columns
)
from nba_ml.feature_engineering.rolling import RollingCategory
from nba_ml.feature_engineering.samples import OUTPUT, GameHistory, split_into_histories
from nba_ml.feature_engineering.situations import SituationalStat
from nba_ml.stores import team_games as team_game_store

ROLLING_WINDOW = 15
"""How many recent games the flat form columns average, which is about five weeks of a season."""

# How fast the weighted form columns forget, in games. A starting choice rather than a swept one:
# a team changes more slowly than a player's role does, so it forgets more slowly than the one game
# halflife the player models measured.
RECENT_FORM_HALFLIFE = 3

SEASON_WINDOW = 82
"""A full regular season of games, which is how far back the steady level columns read."""

# How much history a prediction reads out of the database. Every window above fits inside it, so a
# predicted game's columns come out the same as they would from a build over everything held.
HISTORICAL_WINDOW_LENGTH_YEARS = 5

# How many games a team must already have played before one of its games can be a sample. One is the
# floor rather than a choice: the sequence a model reads cannot be empty.
MINIMUM_PAST_GAMES = 1

PAST_MEAN_PREFIX = "PAST_MEAN_"
PAST_WEIGHTED_MEAN_PREFIX = "PAST_WEIGHTED_MEAN_"
PAST_SEASON_MEAN_PREFIX = "PAST_SEASON_MEAN_"
PAST_SEASON_STD_PREFIX = "PAST_SEASON_STD_"

# WHERE A ROW IS FOUND: #
TEAM_ID = team_game_store.TEAM_ID.category_name
GAME_ID = team_game_store.GAME_ID.category_name
GAME_DATE = team_game_store.GAME_DATE.category_name
OPPONENT_TEAM_ID = team_columns.OPPONENT_PREFIX + TEAM_ID

# WHAT A GAME HOLDS: #
WIN = team_game_store.WIN_LOSS.category_name
"""The win or loss column, which the build rewrites as one for a win."""

WON, LOST = 0, 1
"""
Which position of a two category answer each result is, for a model fit to say who wins.

A model answering in named categories is fit against the position it should answer with, and a
reader is led with the first one, so a win comes first. A family naming the two categories orders
them this way.
"""

WIN_CATEGORY = 'WIN_CATEGORY'
"""
The same result as one of those positions rather than as a flag.

WIN stays one for a win, because it is a stat the build averages and the mean of it is a win rate.
This is only ever a value to be fit against, so no model reads it as a feature.
"""

IS_HOME_ROW = 'IS_HOME_ROW'
"""
True on the home team's row of a game, which is the side a game statistic is read off.

HOME_OR_AWAY is one for away, so a family wanting the home row needs the opposite of it. That
inversion is written down once, here, rather than in each family that reads it.
"""

# Points per possession and the four factors were measured on 2026-08-11 and taken out again. They
# read worse than the raw counts they are worked out from, on a build that already carries
# possessions, and they cost forty columns. Do not add them back without new evidence.

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
"""
What both teams record separately in a game, and what is carried over from one row to the other.

Each is worth reading twice: once for what the team did, and once for what it let the other side do,
which is the only defensive reading a box score carries.
"""

OWN_GAME_STATS = COPIED_FROM_THE_OTHER_SIDE + [
    team_game_store.MINUTES_PLAYED.category_name,
    WIN,
    team_columns.POINT_DIFFERENTIAL,
    team_columns.GAME_TOTAL
]
"""
The same, plus what only reads from the team's own side.

Minutes are the same number for both teams and say whether the game went to overtime. The result and
the two point totals are already both teams together, so neither has an opposing version.
"""

ALLOWED_GAME_STATS = [
    team_columns.OPPONENT_PREFIX + stat for stat in COPIED_FROM_THE_OTHER_SIDE
]
"""The opposing team's own line in the same game, read as what the team allowed."""

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
"""
The stats also carried weighted towards the newest games.

A flat window is slow to notice a team that has changed, through a trade or an injury, and both
readings together say more than either alone. Only the columns that move a score are worth the
second reading.
"""

SEASON_LEVEL_STATS = [
    game_columns.POINTS,
    team_columns.OPPONENT_PREFIX + game_columns.POINTS,
    team_columns.POINT_DIFFERENTIAL,
    team_columns.GAME_TOTAL,
    team_columns.POSSESSIONS
]
"""
What a team's level and its steadiness are read off, over a season length window.

The standard deviation is what separates a team that scores 110 every night from one averaging the
same across 90 and 130, which is most of what the tails of a distribution are made of.
"""

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
"""Where a game sits in the schedule and in the season, which is known before it is played."""

OPPONENT_CONTEXT_STATS = [
    schedule_columns.REST,
    schedule_columns.BREAK_LENGTH,
    season_columns.SEASON_GAME_NUMBER,
    season_columns.TEAM_WIN_PERCENTAGE
] + schedule_columns.get_recent_game_count_columns()
"""
The opposing team's own schedule and record, which decide a game as much as the team's own do.

Home or away and the season phase are left out, because both teams already share them.
"""

SITUATIONS = [situations.IN_THIS_SEASON_TYPE, situations.AT_HOME_OR_AWAY]
"""
Which kinds of game a team's own form is read in. See feature_engineering/situations.py.

Measured on the point differential over three seeds on 2026-08-11. These two beat reading none on
every seed, and adding the team's form against the side it faces on top of them was worth nothing.
Two teams meet a handful of times a season and neither roster is the one that met last time, so
there is little there to read.
"""

class TargetValue(Enum):
    """Which finished column of this build holds a value a model can be fit against."""

    POINT_DIFFERENTIAL = team_columns.POINT_DIFFERENTIAL
    TEAM_POINTS = game_columns.POINTS
    GAME_TOTAL = team_columns.GAME_TOTAL
    RESULT = WIN_CATEGORY

# WHICH COLUMNS A MODEL READS: #
@dataclass(frozen=True)
class FeatureSet():
    """
    Every column name and rolling definition a model built on these rows needs.

    Resolved once per run and passed down, so two models being built at the same time never share
    column state.
    """

    output_column: str
    """The finished column the value being predicted is read off."""

    rolling_categories: list[RollingCategory]
    situational_stats: list[SituationalStat]
    """What a team's form in games like this one is read over. See feature_engineering/situations.py."""

    columns_copied_from_opponent: list[str]
    """The team columns worth carrying over to the row of the team it is playing."""

    sequence_columns: list[str]
    """Read for each of the team's past games."""

    static_columns: list[str]
    """Read once, off the game being predicted."""

def build_feature_set(target: TargetValue, dropped_static_columns: tuple[str, ...] = ()) -> FeatureSet:
    """
    Resolves the columns a model predicting the given value reads.

    Args:
        dropped_static_columns names columns to leave off the game being predicted. A family whose
        samples all read the same value of one has nothing to learn from it.
    """

    rolling_categories = (
        [
            RollingCategory(PAST_MEAN_PREFIX + stat, stat, rolling.MEAN_FUNCTION, ROLLING_WINDOW)
            for stat in OWN_GAME_STATS + ALLOWED_GAME_STATS
        ] + [
            RollingCategory(
                PAST_WEIGHTED_MEAN_PREFIX + stat,
                stat,
                rolling.MEAN_FUNCTION,
                halflife=RECENT_FORM_HALFLIFE
            )
            for stat in RECENT_FORM_STATS
        ] + [
            RollingCategory(PAST_SEASON_MEAN_PREFIX + stat, stat, rolling.MEAN_FUNCTION, SEASON_WINDOW)
            for stat in SEASON_LEVEL_STATS
        ] + [
            RollingCategory(PAST_SEASON_STD_PREFIX + stat, stat, rolling.STD_FUNCTION, SEASON_WINDOW)
            for stat in SEASON_LEVEL_STATS
        ]
    )

    # How the team does in games like this one, measured against the recent form above rather than
    # against a whole season, so a team that has changed is not read as its old self.
    situational_stats = [
        SituationalStat(stat, stat, PAST_MEAN_PREFIX + stat) for stat in SEASON_LEVEL_STATS
    ]
    situational_columns = situations.all_columns(SITUATIONS, situational_stats)

    # Everything the team knows about itself going into the game, read a second time off the side it
    # is facing. That is what makes one row describe a whole game rather than half of one.
    columns_copied_from_opponent = (
        [category.column_name for category in rolling_categories]
        + situational_columns
        + OPPONENT_CONTEXT_STATS
    )
    opponent_columns = [
        team_columns.OPPONENT_PREFIX + column for column in columns_copied_from_opponent
    ]

    return FeatureSet(
        output_column=target.value,
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
                + opponent_columns
            )
            - set(dropped_static_columns)
        )
    )

# BUILDING THE ROWS: #
def ordered_by_team_and_date(team_game_data: pd.DataFrame) -> pd.DataFrame:
    """
    Every grouped column below reads a team's games in the order they happened, and cutting the
    finished frame into histories needs each team's games to sit together.
    """

    return team_game_data.sort_values(by=[TEAM_ID, GAME_DATE]).reset_index(drop=True)

def build_rows(features: FeatureSet, team_game_data: pd.DataFrame) -> pd.DataFrame:
    """
    Returns every team game with its own state going into it and the opposing team's.

    The given frame is modified, so hand it a copy where the caller still needs the original.
    """

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
    # A row whose matchup says neither reads as away, so it simply never anchors a game sample.
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

    # The opposing team's own line in each game, which is both what the team allowed and the half of
    # the result it does not record itself.
    team_game_data = team_columns.add_opponent_stat_columns(
        team_game_data,
        GAME_ID,
        TEAM_ID,
        COPIED_FROM_THE_OTHER_SIDE
        )
    team_game_data = team_columns.add_game_result_columns(
        team_game_data,
        game_columns.POINTS,
        team_columns.OPPONENT_PREFIX + game_columns.POINTS
        )

    team_game_data = ordered_by_team_and_date(team_game_data)
    team_game_data = rolling.add_rolling_function_columns(
        team_game_data,
        features.rolling_categories,
        group_by_column=TEAM_ID
        )

    # After the rolling columns, because a team's form in a kind of game is measured against them.
    team_game_data = situations.add_columns(
        team_game_data,
        TEAM_ID,
        SITUATIONS,
        features.situational_stats
        )

    # Last, because it carries the finished rolling columns over to the row of the team being played.
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
    sample_row_column: str | None = None,
    print_debug: bool = False
    ) -> dict[int, GameHistory]:
    """
    Turns raw team games into one finished history per team.

    The given frame is not modified, so this can be called more than once on the same data.

    Args:
        sample_row_column names a column that is true for the rows a sample may be read off. Leave
        it unset where both sides of a game are samples.
    """

    if print_debug:
        print("Feature engineering team game data...")

    team_game_data = build_rows(features, team_game_data.copy())
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

# THE GAME BEING PREDICTED: #
def read_history_window(target_game: Game) -> pd.DataFrame:
    """Every stored team game near enough to the predicted one to reach any window the build uses."""

    started = target_game.date - relativedelta(years=HISTORICAL_WINDOW_LENGTH_YEARS)

    return team_game_store.get_game_data_after_date(started).dropna()

def find_target_game(
    histories: dict[int, GameHistory],
    team_id: int,
    target_game: Game
    ) -> tuple[GameHistory, int] | None:
    """
    A team's finished history and where the game being predicted sits in it.

    Returns None when the build cannot answer for that team, which means one of two things a caller
    words the same way: nothing is stored for it near the predicted date, or too little sits in front
    of the game for a sequence to be read.

    Raises:
        ValueError if the placeholder rows did not survive the build as exactly one row per team,
        which is a fault in the build rather than something a caller asked for.
    """

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
