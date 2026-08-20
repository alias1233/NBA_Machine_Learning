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

COMBINED_GAME_STATS = [
    game_columns.POINTS,
    game_columns.REBOUNDS,
    team_game_store.ASSISTS.category_name,
    team_game_store.THREE_POINTERS_MADE.category_name
]
"""
What both teams record together, which is what a statistic belonging to the whole game is read off.

Each is the same number on either row of a game, so a model predicting one names no team. The points
total is read by far more than the model predicting it, so team_columns names it GAME_TOTAL as well.
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

READS_CORE_ROSTER = True
"""
Whether a row carries who the team has gained, lost and is missing.

A box score says what a team did and nothing about who was on the floor to do it, so without this a
model reads a side missing its best player as the side that played last week. See
feature_engineering/team_rosters.py.

It is read off the game being predicted and not off each past game. That is where the reader's own
answer changes, and reading it inside the sequence would mean publishing the whole league's rosters
the way the player family publishes its build, because a prediction would then have to fill it in for
every past game of both teams. Worth trying if a measurement ever asks for it.

Turning it off changes which columns a row carries rather than what they hold, so a model fit one way
simply cannot answer the other, and models/loading.py is what catches that. It is written down here
so the two can be measured against each other.
"""

def _allowed(stat: str) -> str:
    """What the team let the other side record, which is the only defensive reading a box score has."""

    return team_columns.OPPONENT_PREFIX + stat

@dataclass(frozen=True)
class TargetColumns():
    """
    The columns predicting one value needs on top of the ones every model of these families gets.

    The always on lists above already carry the whole box score, both sides of it, and a flat recent
    average of every one of them. What a target adds is the second and third readings of whatever it
    is actually about: a form weighted towards the newest games, and a season length level and
    steadiness. Those are the readings the points models were given because points are what they
    predict, so a model predicting something else asks for them of its own statistic.

    Adding a model to either family means adding one of these and nothing else.
    """

    output_column: str
    """The finished column the value being predicted is read off."""

    mean_stats: tuple[str, ...] = ()
    """
    Stats to carry a flat recent average of, on top of the box score every model already gets. Only a
    combined stat needs listing here, since a raw one and its opposing version are always covered.
    """

    recent_form_stats: tuple[str, ...] = ()
    """Stats to read a second time weighted towards the newest games."""

    season_level_stats: tuple[str, ...] = ()
    """
    Stats to carry a season length mean and standard deviation of, and to read in a kind of game.
    The standard deviation is most of what the tails of a distribution are made of.
    """

class TargetValue(Enum):
    """
    Which finished column of this build a model is fit against, and what it reads on top of the
    always on columns above.
    """

    POINT_DIFFERENTIAL = TargetColumns(team_columns.POINT_DIFFERENTIAL)
    TEAM_POINTS = TargetColumns(game_columns.POINTS)
    GAME_TOTAL = TargetColumns(team_columns.GAME_TOTAL)
    RESULT = TargetColumns(WIN_CATEGORY)

    # A rebound is a missed shot nobody has picked up yet, so how many are there to win is decided by
    # how much each side shoots and how well, and how many the team takes is its own board strength.
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

    # An assist is a made field goal somebody passed to, so both halves of that are read, and the
    # side faced is read for how many it lets teams record.
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

    # How many a team makes is how many it takes and how often they go in, and how many the side it
    # faces gives up from behind the line.
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

    # The same three again as one number for the whole game. Each reads its own combined column, so
    # the model is handed the figure it is fit against rather than left to add two together, and
    # each side's own half beside it, because two teams' recent games are two different runs of form.
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

    What every model gets is the whole box score both ways round and everything that moves a score.
    What the target adds is the same readings of its own statistic. See TargetColumns.

    Args:
        dropped_static_columns names columns to leave off the game being predicted. A family whose
        samples all read the same value of one has nothing to learn from it.
    """

    columns = target.value

    def gather(always: list[str], selected: tuple[str, ...]) -> list[str]:
        """The always on stats and whatever the target asked for, in a stable order."""

        return sorted(set(always) | set(selected))

    # Anything given a weighted or a season length reading gets the flat one too, because that is
    # what the other two are read against and what a situational column is measured off.
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

    # How the team does in games like this one, measured against the recent form above rather than
    # against a whole season, so a team that has changed is not read as its old self.
    situational_stats = [
        SituationalStat(stat, stat, PAST_MEAN_PREFIX + stat) for stat in season_level_stats
    ]
    situational_columns = situations.all_columns(SITUATIONS, situational_stats)

    core_roster_columns = team_rosters.all_columns() if READS_CORE_ROSTER else []

    # Everything the team knows about itself going into the game, read a second time off the side it
    # is facing. That is what makes one row describe a whole game rather than half of one, and it is
    # why naming the players missing from either side changes the answer.
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

# WHO EACH TEAM HAS: #
def stored_roster_totals(team_game_data: pd.DataFrame) -> CoreRosterTotals | None:
    """
    The roster reading a build over stored games needs, or None where these rows do not read one.

    Both families ask for it the same way, so which of the two it is lives here rather than in each.
    """

    return team_rosters.stored_totals(team_game_data) if READS_CORE_ROSTER else None

def prediction_roster_totals(
    target_game: Game,
    rosters: Mapping[int, RosterScenario]
    ) -> CoreRosterTotals | None:
    """
    The roster reading of the two rows standing for the game being predicted, or None as above.

    Args:
        rosters is the change each side is making, keyed by team id. A side left out plays whoever
        played its last game, which is all the stored data says.
    """

    return team_rosters.prediction_totals(target_game, rosters) if READS_CORE_ROSTER else None

# BUILDING THE ROWS: #
def ordered_by_team_and_date(team_game_data: pd.DataFrame) -> pd.DataFrame:
    """
    Every grouped column below reads a team's games in the order they happened, and cutting the
    finished frame into histories needs each team's games to sit together.
    """

    return team_game_data.sort_values(by=[TEAM_ID, GAME_DATE]).reset_index(drop=True)

def build_rows(
    features: FeatureSet,
    team_game_data: pd.DataFrame,
    roster_totals: CoreRosterTotals | None
    ) -> pd.DataFrame:
    """
    Returns every team game with its own state going into it and the opposing team's.

    The given frame is modified, so hand it a copy where the caller still needs the original.

    Args:
        roster_totals is who each team had available, out of feature_engineering/team_rosters.py.
        None only where READS_CORE_ROSTER is off, since otherwise the rows would read as thirty
        teams nobody is ever missing from.
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
    team_game_data = team_columns.add_point_differential_column(
        team_game_data,
        game_columns.POINTS,
        team_columns.OPPONENT_PREFIX + game_columns.POINTS
        )
    team_game_data = team_columns.add_combined_stat_columns(team_game_data, COMBINED_GAME_STATS)

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

    # Before the copy below, so a row also carries who the side it faces is missing.
    if READS_CORE_ROSTER:
        if roster_totals is None:
            raise ValueError(
                "These rows read who each team has available, so a build has to be given the roster "
                "reading. See feature_engineering/team_rosters.py."
            )

        team_game_data = team_rosters.add_columns(team_game_data, roster_totals)

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
    roster_totals: CoreRosterTotals | None,
    sample_row_column: str | None = None,
    print_debug: bool = False
    ) -> dict[int, GameHistory]:
    """
    Turns raw team games into one finished history per team.

    The given frame is not modified, so this can be called more than once on the same data.

    Args:
        roster_totals is who each team had available. See build_rows.
        sample_row_column names a column that is true for the rows a sample may be read off. Leave
        it unset where both sides of a game are samples.
    """

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

# THE GAME BEING PREDICTED: #
def read_history_window(target_game: Game) -> pd.DataFrame:
    """Every stored team game near enough to the predicted one to reach any window the build uses."""

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
