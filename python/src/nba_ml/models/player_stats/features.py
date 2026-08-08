"""
Turning the stored box scores into the inputs a player game statistics model reads.

The same feature build runs for training and for a prediction, so a predicted game is fed through it
as one more row rather than assembled by hand.
"""

from dataclasses import dataclass
from datetime import datetime
from dateutil.relativedelta import relativedelta
from enum import Enum
from typing import Any, Collection, Iterable

import pandas as pd
import numpy as np

from nba_ml import season
from nba_ml.entities import Game
from nba_ml.feature_engineering import game_columns, rolling
from nba_ml.feature_engineering.rolling import RollingCategory
from nba_ml.machine_learning.datasets import PlayerGameSequences, SequenceInputSamples
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.stores import player_games, players, team_games

ROLLING_WINDOW = 15

# How fast the weighted recent form columns forget, in games. Swept against flat windows and beat
# all of them on every stat.
RECENT_FORM_HALFLIFE = 1

# How much history a prediction reads out of the databases.
HISTORICAL_WINDOW_LENGTH_YEARS = 5

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
    player_games.WIN_LOSS.category_name
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

# INPUT OUTPUT STRUCTURE: #
OUTPUT = "OUTPUT"

# How many games a player must already have played before one of their games can be a sample.
# Players who never reach it are dropped from the dataset.
MINIMUM_PAST_GAMES = 20

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

    opponent_allowed_team_stats: tuple[str, ...] = ()
    """Team stats to measure against the team's own recent average, then average per opponent."""

class TargetStat(Enum):
    POINTS = TargetStatColumns(
        output_column=game_columns.POINTS + game_columns.PLAYER_SUFFIX,
        sequence_stats=(
            game_columns.POINTS + game_columns.PLAYER_SUFFIX,
            player_games.OFFENSIVE_REBOUNDS.category_name + game_columns.PLAYER_SUFFIX,
            team_games.ASSISTS.category_name + game_columns.TEAM_SUFFIX,
            player_games.TURNOVERS.category_name + game_columns.PLAYER_SUFFIX,
            player_games.FIELD_GOALS_ATTEMPTED.category_name + game_columns.PLAYER_SUFFIX,
            player_games.FIELD_GOALS_MADE.category_name + game_columns.PLAYER_SUFFIX,
            player_games.THREE_POINTERS_ATTEMPTED.category_name + game_columns.PLAYER_SUFFIX,
            player_games.THREE_POINTERS_MADE.category_name + game_columns.PLAYER_SUFFIX,
            player_games.FREE_THROWS_ATTEMPTED.category_name + game_columns.PLAYER_SUFFIX,
            player_games.FREE_THROWS_MADE.category_name + game_columns.PLAYER_SUFFIX,
        ),
        career_stats=(game_columns.POINTS,),
        player_recent_mean_stats=(game_columns.POINTS,),
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
        output_column=game_columns.REBOUNDS + game_columns.PLAYER_SUFFIX,
        sequence_stats=(
            player_games.OFFENSIVE_REBOUNDS.category_name + game_columns.PLAYER_SUFFIX,
            player_games.DEFENSIVE_REBOUNDS.category_name + game_columns.PLAYER_SUFFIX,
            team_games.FIELD_GOALS_ATTEMPTED.category_name + game_columns.TEAM_SUFFIX,
            team_games.FIELD_GOALS_MADE.category_name + game_columns.TEAM_SUFFIX,
            team_games.THREE_POINTERS_ATTEMPTED.category_name + game_columns.TEAM_SUFFIX,
            team_games.THREE_POINTERS_MADE.category_name + game_columns.TEAM_SUFFIX,
        ),
        career_stats=(
            player_games.OFFENSIVE_REBOUNDS.category_name,
            player_games.DEFENSIVE_REBOUNDS.category_name,
        ),
        player_recent_mean_stats=(game_columns.REBOUNDS,),
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
        output_column=player_games.ASSISTS.category_name + game_columns.PLAYER_SUFFIX,
        sequence_stats=(
            player_games.ASSISTS.category_name + game_columns.PLAYER_SUFFIX,
            player_games.TURNOVERS.category_name + game_columns.PLAYER_SUFFIX,
            player_games.FIELD_GOALS_ATTEMPTED.category_name + game_columns.TEAM_SUFFIX,
            player_games.FIELD_GOALS_MADE.category_name + game_columns.TEAM_SUFFIX,
            player_games.THREE_POINTERS_ATTEMPTED.category_name + game_columns.TEAM_SUFFIX,
            player_games.THREE_POINTERS_MADE.category_name + game_columns.TEAM_SUFFIX,
        ),
        career_stats=(player_games.ASSISTS.category_name,),
        opponent_allowed_team_stats=(
            team_games.ASSISTS.category_name,
            team_games.TURNOVERS.category_name,
            team_games.FIELD_GOALS_ATTEMPTED.category_name,
            team_games.FIELD_GOALS_MADE.category_name,
            team_games.THREE_POINTERS_ATTEMPTED.category_name,
            team_games.THREE_POINTERS_MADE.category_name,
        )
    )

# Columns every model gets, whatever it is predicting.
SEQUENCE_STATS_ALWAYS = [
    player_games.MINUTES_PLAYED.category_name + game_columns.PLAYER_SUFFIX,
    game_columns.POINTS + game_columns.TEAM_SUFFIX,
    game_columns.OPPONENT_PREFIX + game_columns.POINTS,
    player_games.PLUS_MINUS.category_name,
    player_games.PERSONAL_FOULS.category_name + game_columns.PLAYER_SUFFIX,
    game_columns.HOME_OR_AWAY, game_columns.REST, game_columns.BREAK_LENGTH,
    game_columns.SEASON_OPENER, game_columns.CAREER_DEBUT,
    game_columns.CHANGED_TEAM,
    game_columns.POSSESSIONS,
    team_games.MINUTES_PLAYED.category_name + game_columns.TEAM_SUFFIX
] + (
    game_columns.ALL_SEASON_TYPES
    + game_columns.ALL_SEASON_CONTEXT_COLUMNS
    + game_columns.ALL_AVAILABILITY_COLUMNS
    + game_columns.get_recent_game_count_columns()
)

# A career debut is left out here, because a game only becomes a sample once MINIMUM_PAST_GAMES sit
# behind it, so the game being predicted is never anyone's first.
STATIC_STATS_ALWAYS = [
    game_columns.AGE_DURING_GAME, game_columns.NBA_EXPERIENCE_DURING_GAME,
    game_columns.HOME_OR_AWAY, game_columns.REST, game_columns.BREAK_LENGTH,
    game_columns.SEASON_OPENER,
    game_columns.CHANGED_TEAM,
    game_columns.GAMES_PLAYED
] + (
    game_columns.ALL_SEASON_TYPES
    + game_columns.ALL_SEASON_CONTEXT_COLUMNS
    + game_columns.ALL_AVAILABILITY_COLUMNS
    + game_columns.get_recent_game_count_columns()
)

OPPONENT_ALLOWED_TEAM_STATS_ALWAYS = [
    team_games.PERSONAL_FOULS.category_name
]
CAREER_STATS_ALWAYS: list[str] = []

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
    """Summed together to form the value being predicted."""

    player_rolling_categories: list[RollingCategory]

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
        return player_column + game_columns.PLAYER_SUFFIX

    return player_column

def build_feature_set(target_stats: Iterable[TargetStat]) -> FeatureSet:
    """
    Resolves the columns a model predicting the given stats needs. Predicting several stats at once
    takes the union of what each one asks for.
    """

    specifications = [target_stat.value for target_stat in set(target_stats)]

    def gather(always: list[str], selected: list[tuple[str, ...]]) -> list[str]:
        """Merges the always on columns with what each targeted stat asked for, in a stable order."""

        return sorted(set(always).union(*selected))

    career_stats = gather(CAREER_STATS_ALWAYS, [spec.career_stats for spec in specifications])
    player_recent_mean_stats = gather(
        PLAYER_RECENT_MEAN_STATS_ALWAYS,
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
            game_columns.OPPONENT_PREFIX + PAST_MEAN_ALLOWED_INFIX + stat,
            stat,
            rolling.MEAN_FUNCTION,
            ROLLING_WINDOW
        ) for stat in team_stats_over_mean_columns
    ]

    # How the opposing team's own season is going, which is what tells a model whether the game
    # still matters to them. Only their record is carried over, since both teams share the calendar.
    opponent_record_column = game_columns.OPPONENT_PREFIX + game_columns.TEAM_WIN_PERCENTAGE

    # Who the team gained, lost and is missing around the player, measured in the same recent
    # averages the player's own form is measured in.
    core_teammate_stat_columns = [category.column_name for category in player_mean_categories]
    core_teammate_columns = game_columns.get_core_teammate_columns(core_teammate_stat_columns)

    sequence_columns = sorted(set(
        SEQUENCE_STATS_ALWAYS
        + [stat for spec in specifications for stat in spec.sequence_stats]
        + [category.column_name for category in opponent_allowed_team_categories]
        + [opponent_record_column]
        + core_teammate_columns
    ))

    # The player's own recent average of each targeted stat. Recent form is the strongest single
    # predictor here, and without this the model would have to rebuild it from the raw past games.
    team_rolling_column_names = {category.column_name for category in team_allowed_mean_categories}
    recent_form_columns = [
        _column_name_after_merge(category.column_name, team_rolling_column_names)
        for category in player_mean_categories + player_weighted_mean_categories
    ]

    static_columns = sorted(set(
        STATIC_STATS_ALWAYS
        + [category.column_name for category in career_categories]
        + [category.column_name for category in opponent_allowed_team_categories]
        + [opponent_record_column]
        + recent_form_columns
        + core_teammate_columns
    ))

    return FeatureSet(
        output_columns=sorted({spec.output_column for spec in specifications}),
        player_rolling_categories=career_categories + player_mean_categories + player_weighted_mean_categories,
        core_teammate_stat_columns=core_teammate_stat_columns,
        team_rolling_categories=team_allowed_mean_categories,
        team_difference_columns=team_difference_columns,
        opponent_rolling_categories=opponent_allowed_team_categories,
        opponent_columns_to_copy=[
            team_games.TEAM_ID.category_name,
            game_columns.POINTS,
            game_columns.TEAM_WIN_PERCENTAGE
        ],
        sequence_columns=sequence_columns,
        static_columns=static_columns
    )

# PREPROCESSED DATA: #
@dataclass(frozen=True)
class PlayerGameHistory():
    """
    One player's games, already reduced to the numbers a model reads, oldest game first.

    Everything is a plain array rather than a dataframe, so building a sample is a slice instead of
    hundreds of thousands of small pandas objects.
    """

    static_player_info: np.ndarray
    """The player's own unchanging information, shaped (player info features,)."""

    game_ids: np.ndarray
    game_dates: np.ndarray
    sequence_values: np.ndarray
    """Shaped (games, sequence features)."""

    static_values: np.ndarray
    """Shaped (games, static features)."""

    opponent_team_ids: np.ndarray
    outputs: np.ndarray

    @property
    def game_count(self) -> int:
        return len(self.game_dates)

    def static_input(self, index: int) -> np.ndarray:
        """The static half of one sample's input, read off the game being predicted."""

        return np.concatenate((self.static_player_info, self.static_values[index]))

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

    player_info[players.BIRTHDATE.category_name] = pd.to_datetime(
        player_info[players.BIRTHDATE.category_name]
        )
    player_info[players.FROM_YEAR.category_name] = pd.to_datetime(
        player_info[players.FROM_YEAR.category_name], format='%Y'
        )
    player_info = game_columns.convert_height_to_inches(
        player_info,
        players.HEIGHT.category_name,
        fill_unknown_with_mean=True
    )
    player_info = game_columns.encode_undrafted(
        player_info,
        players.DRAFT_NUMBER.category_name
    )
    player_info = game_columns.handle_unknown_weight(
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
    Returns every game played by a player with enough games to model, sorted by player and then by
    date so that the grouped columns below read each player's games in the order they happened.
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
    player_game_data = game_columns.add_age_during_game_column(
        player_game_data,
        player_info,
        players.PLAYER_ID.category_name,
        player_games.PLAYER_ID.category_name,
        players.BIRTHDATE.category_name,
        player_games.GAME_DATE.category_name
    )
    player_game_data = game_columns.add_years_NBA_experience_during_game_column(
        player_game_data,
        player_info,
        players.PLAYER_ID.category_name,
        player_games.PLAYER_ID.category_name,
        players.FROM_YEAR.category_name,
        player_games.GAME_DATE.category_name
    )

    player_id = player_game_data[player_games.PLAYER_ID.category_name]
    games_played = player_id.groupby(player_id, sort=False).transform('size')
    player_game_data = player_game_data[
        (games_played >= MINIMUM_PAST_GAMES)
        & player_id.isin(player_info[players.PLAYER_ID.category_name])
    ]
    player_game_data = player_game_data.sort_values(
        by=[player_games.PLAYER_ID.category_name, player_games.GAME_DATE.category_name]
        ).reset_index(drop=True)

    player_game_data = game_columns.add_break_columns(
        player_game_data,
        player_games.GAME_DATE.category_name,
        group_by_column=player_games.PLAYER_ID.category_name
        )
    player_game_data = game_columns.add_changed_team_column(
        player_game_data,
        player_games.TEAM_ID.category_name,
        group_by_column=player_games.PLAYER_ID.category_name
    )
    player_game_data = game_columns.add_games_played_column(
        player_game_data,
        player_games.PLAYER_ID.category_name
    )
    player_game_data = game_columns.add_recent_game_count_columns(
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
    team_game_data = game_columns.add_possessions_column(
        team_game_data,
        team_games.FIELD_GOALS_ATTEMPTED.category_name,
        team_games.FREE_THROWS_ATTEMPTED.category_name,
        team_games.OFFENSIVE_REBOUNDS.category_name,
        team_games.TURNOVERS.category_name
        )
    team_game_data = game_columns.add_encoded_season_type_columns(
        team_game_data,
        team_games.GAME_ID.category_name
        )
    team_game_data = game_columns.add_encoded_home_or_away_column(
        team_game_data,
        team_games.MATCHUP.category_name
        )
    team_game_data = game_columns.encode_win_loss_column_as_integer(
        team_game_data,
        team_games.WIN_LOSS.category_name
    )
    team_game_data = game_columns.add_season_standings_columns(
        team_game_data,
        team_games.GAME_DATE.category_name,
        team_games.TEAM_ID.category_name,
        team_games.WIN_LOSS.category_name,
        game_columns.REGULAR_SEASON
    )

    team_game_data = rolling.add_rolling_function_columns(
        team_game_data,
        features.team_rolling_categories,
        group_by_column=team_games.TEAM_ID.category_name
    )
    team_game_data = game_columns.add_opponent_stat_columns(
        team_game_data,
        team_games.GAME_ID.category_name,
        team_games.TEAM_ID.category_name,
        features.opponent_columns_to_copy
        )
    team_game_data = game_columns.add_differences_columns(
        team_game_data,
        features.team_difference_columns
    )

    opponent_team_id_column = game_columns.OPPONENT_PREFIX + team_games.TEAM_ID.category_name
    team_game_data = team_game_data.sort_values(
        by=[opponent_team_id_column, team_games.GAME_DATE.category_name]
        ).reset_index(drop=True)

    return rolling.add_rolling_function_columns(
        team_game_data,
        features.opponent_rolling_categories,
        group_by_column=opponent_team_id_column
    )

def _split_into_player_histories(
    features: FeatureSet,
    player_info_features: dict[int, np.ndarray],
    player_team_game_data: pd.DataFrame
    ) -> dict[int, PlayerGameHistory]:
    """
    Cuts the finished feature frame into one history per player.

    The columns are pulled out as whole arrays once and then sliced, since every player's games sit
    together in the frame.
    """

    player_id_column = player_games.PLAYER_ID.category_name
    opponent_team_id_column = game_columns.OPPONENT_PREFIX + team_games.TEAM_ID.category_name

    game_ids = player_team_game_data[team_games.GAME_ID.category_name].to_numpy()
    game_dates = player_team_game_data[team_games.GAME_DATE.category_name].to_numpy()
    sequence_values = player_team_game_data[features.sequence_columns].to_numpy(dtype=np.float32)
    static_values = player_team_game_data[features.static_columns].to_numpy(dtype=np.float32)
    opponent_team_ids = player_team_game_data[opponent_team_id_column].to_numpy(dtype=np.int64)
    outputs = player_team_game_data[OUTPUT].to_numpy(dtype=np.float64)

    histories: dict[int, PlayerGameHistory] = {}
    for player_id, positions in player_team_game_data.groupby(by=player_id_column, sort=False).indices.items():
        player_id = int(player_id)
        start, stop = int(positions[0]), int(positions[-1]) + 1

        if stop - start != len(positions):
            raise ValueError("Every player's games must sit together, so the frame has to be sorted by player first.")

        histories[player_id] = PlayerGameHistory(
            static_player_info=player_info_features[player_id],
            game_ids=game_ids[start:stop],
            game_dates=game_dates[start:stop],
            sequence_values=sequence_values[start:stop],
            static_values=static_values[start:stop],
            opponent_team_ids=opponent_team_ids[start:stop],
            outputs=outputs[start:stop]
        )

    return histories

def _preprocess_game_data(
        features: FeatureSet,
        player_info: pd.DataFrame,
        player_game_data: pd.DataFrame,
        team_game_data: pd.DataFrame,
        print_debug: bool = False
        ) -> dict[int, PlayerGameHistory]:
    """
    Turns the raw tables into one finished history per player.

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
    player_game_data = game_columns.add_availability_columns(
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
    player_game_data = game_columns.add_core_teammate_columns(
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

    player_team_game_data = game_columns.merge_player_team_game_data(
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

    player_team_game_data[OUTPUT] = player_team_game_data[features.output_columns].sum(axis=1)

    histories = _split_into_player_histories(
        features,
        _build_player_info_features(player_info),
        player_team_game_data
    )

    if print_debug:
        print("Finished generating game data.")

    return histories

def _get_all_preprocessed_game_data(
        features: FeatureSet,
        print_debug: bool = False
    ) -> dict[int, PlayerGameHistory]:

    if print_debug:
        print("Querying data from databases...")

    all_player_info: pd.DataFrame = players.get_all_players_info().drop(columns=[players.PLAYER_NAME.category_name])
    all_player_info = all_player_info.dropna()

    all_player_game_data: pd.DataFrame = player_games.get_all_player_game_data()
    all_player_game_data = all_player_game_data.dropna()

    all_team_game_data: pd.DataFrame = team_games.get_all_team_game_data()
    all_team_game_data = all_team_game_data.dropna()

    return _preprocess_game_data(features, all_player_info, all_player_game_data, all_team_game_data, print_debug)

# SPLITTING INTO TRAINING, VALIDATION, AND TEST: #
TRAINING_SPLIT = 0
VALIDATION_SPLIT = 1
TEST_SPLIT = 2

def _get_split_start_dates(
    validation_split_start_date: datetime,
    test_split_start_date: datetime
    ) -> np.ndarray:
    return np.array([validation_split_start_date, test_split_start_date], dtype='datetime64[ns]')

def _get_split_of_every_game(
    history: PlayerGameHistory,
    split_start_dates: np.ndarray
    ) -> np.ndarray:
    """
    Which split each game belongs to. A game on a split's start date stays in the earlier split, so
    that a model is only ever tested on games played after the ones it learned from.
    """

    return np.searchsorted(split_start_dates, history.game_dates, side='left')

def _print_progress(count: int):
    if count % 25000 == 0:
        print(f"\r\033[KData Chunks Processed: {count}", end="", flush=True)

# TRAINING DATA: #
def _get_player_info_width(histories: dict[int, PlayerGameHistory]) -> int:
    """How many columns a player's own information takes up, which is the same for every player."""

    return next((len(history.static_player_info) for history in histories.values()), 0)

class _SampleAccumulator():
    """Collects the samples of one split before they are packed into arrays."""

    def __init__(self):
        self.player_indices: list[int] = []
        self.sequence_end_indices: list[int] = []
        self.opponent_team_ids: list[int] = []
        self.static_inputs: list[np.ndarray] = []
        self.outputs: list[float] = []

    def add(
        self,
        player_index: int,
        sequence_end_index: int,
        opponent_team_id: int,
        static_input: np.ndarray,
        output: float
        ):
        self.player_indices.append(player_index)
        self.sequence_end_indices.append(sequence_end_index)
        self.opponent_team_ids.append(opponent_team_id)
        self.static_inputs.append(static_input)
        self.outputs.append(output)

    def to_samples(self, static_input_dim: int) -> SequenceInputSamples:
        return SequenceInputSamples(
            np.array(self.player_indices, dtype=np.int64),
            np.array(self.sequence_end_indices, dtype=np.int64),
            np.array(self.opponent_team_ids, dtype=np.int64),
            np.stack(self.static_inputs) if self.static_inputs else np.empty((0, static_input_dim), dtype=np.float32),
            np.array(self.outputs, dtype=np.float64)
        )

def get_all_labeled_data(
        features: FeatureSet,
        validation_split_start_date: datetime,
        test_split_start_date: datetime,
        chunk_step_size: int = 1,
        print_debug: bool = False
        ) -> tuple[
            PlayerGameSequences,
            SequenceInputSamples,
            SequenceInputSamples,
            SequenceInputSamples
            ]:
    """
    Builds every labeled sample the league holds, split into training, validation and test by date.

    Each player's games are kept once and the samples only hold where in them to read, so that a
    sample can look back over a long history without storing its own copy of it.

    Games played against the predicted game's opponent are marked inside the sequence itself, so a
    sample is kept even when the player has rarely faced them.

    Returns:
        (games of every player, training samples, validation samples, test samples)
    """

    histories = _get_all_preprocessed_game_data(features, print_debug)

    if print_debug:
        print("Arranging data into training chunks...")

    split_start_dates = _get_split_start_dates(validation_split_start_date, test_split_start_date)
    static_input_dim = _get_player_info_width(histories) + len(features.static_columns)

    player_sequences: list[np.ndarray] = []
    player_opponent_team_ids: list[np.ndarray] = []
    training_game_counts: list[int] = []
    all_samples = [_SampleAccumulator() for _ in range(len(split_start_dates) + 1)]

    count: int = 0
    for player_index, history in enumerate(histories.values()):
        player_sequences.append(history.sequence_values)
        player_opponent_team_ids.append(history.opponent_team_ids)

        splits = _get_split_of_every_game(history, split_start_dates)

        # Only the oldest games are visible to the training split, so the scalers can be fit without
        # seeing validation or test games.
        training_game_counts.append(int((splits == TRAINING_SPLIT).sum()))

        for index in range(MINIMUM_PAST_GAMES, history.game_count, chunk_step_size):
            if print_debug:
                _print_progress(count)
                count += 1

            all_samples[splits[index]].add(
                player_index,
                index,
                int(history.opponent_team_ids[index]),
                history.static_input(index),
                history.outputs[index]
            )

    if print_debug:
        print("")
        print("Finished data processing.")

    player_game_sequences = PlayerGameSequences(
        player_sequences,
        player_opponent_team_ids,
        np.array(training_game_counts, dtype=np.int64)
    )

    return (
        player_game_sequences,
        all_samples[TRAINING_SPLIT].to_samples(static_input_dim),
        all_samples[VALIDATION_SPLIT].to_samples(static_input_dim),
        all_samples[TEST_SPLIT].to_samples(static_input_dim)
    )

# INFERENCE: #
def _check_player_can_be_read(
    target_player_id: int,
    player_info: pd.DataFrame,
    recorded_games: int
    ):
    """
    Refuses a player the feature build would drop, before the build runs.

    _preprocess_player_game_data keeps only players who have stored information and MINIMUM_PAST_GAMES
    games. Left to itself, a dropped player is simply absent at the end, so this says why instead.

    Args:
        recorded_games is how many games the player has stored. The game being predicted is added as
        one more row, which is why it counts towards the minimum.
    """

    if target_player_id not in player_info[players.PLAYER_ID.category_name].values:
        raise PredictionRefused(
            Refusal.MISSING_PLAYER_INFORMATION,
            f"Nothing is stored about player {target_player_id} themselves, which every model reads."
        )

    if recorded_games + 1 < MINIMUM_PAST_GAMES:
        raise PredictionRefused(
            Refusal.TOO_FEW_GAMES,
            f"Player {target_player_id} has {recorded_games} recorded games, and a prediction reads "
            f"{MINIMUM_PAST_GAMES - 1}."
        )

def _get_inference_player_game_data(
    features: FeatureSet,
    target_player_id: int,
    target_player_team_id: int,
    target_game: Game,
    removed_core_teammate_player_ids: Collection[int],
    added_core_teammate_player_ids: Collection[int],
    print_debug: bool = False
    ) -> tuple[PlayerGameHistory, int]:
    """
    Builds every game played by the target player, ending with a placeholder row holding what is
    already known about the game being predicted.

    The placeholder is fed through the same feature build as every other game, so rest and long
    break come from the gap between the target game's date and the player's last recorded game. That
    is only the player's real rest while the databases are current, so collect before predicting.

    Args:
        removed_core_teammate_player_ids are core players from the team's last game who are out for
        this one. added_core_teammate_player_ids are the reverse, players expected back in. Core
        means the minutes cutoff in game_columns.

    Returns:
        (the target player's history, the position of the predicted game within it)
    """

    if print_debug:
        print("Querying data from databases...")

    target_player_opponent_team_id = target_game.opponent_of(target_player_team_id)
    historical_window_start_date = target_game.date - relativedelta(years=HISTORICAL_WINDOW_LENGTH_YEARS)

    # Every player is read, not just the ones still active in the window. A player missing from here
    # is dropped from the game data entirely, which would leave the core teammate columns totalling
    # a smaller roster than the one the model was trained on. The name is dropped because it is held
    # for search and display, and a player without one must not fall out of the data.
    player_info: pd.DataFrame = players.get_all_players_info().drop(columns=[players.PLAYER_NAME.category_name])
    player_info = player_info.dropna()

    player_game_data: pd.DataFrame = player_games.get_game_data_after_date(historical_window_start_date)
    player_game_data = player_game_data.dropna()

    # The target player's whole history is read rather than just the window, because their long
    # window columns are model inputs and a slice of a career would not match what training built.
    # The extra games only feed those columns: a game with no team row drops out when the two merge.
    target_player_game_data = player_games.get_specific_player_game_data(target_player_id).dropna()
    player_game_data = pd.concat([player_game_data, target_player_game_data]).drop_duplicates(
        subset=[player_games.PLAYER_ID.category_name, player_games.GAME_ID.category_name]
    )

    _check_player_can_be_read(target_player_id, player_info, len(target_player_game_data))

    team_game_data: pd.DataFrame = team_games.get_game_data_after_date(historical_window_start_date)
    team_game_data = team_game_data.dropna()

    if print_debug:
        print("Getting previous game player ids...")

    target_game_date_str = season.to_date_string(target_game.date)

    # Get all player ids that played for the target team in the last game it played before this one.
    # Reading its latest game outright would build a game inside recorded history from a roster that
    # only existed later, which makes the core teammate columns read as changes on their own.
    previous_team_games = team_game_data[
        (team_game_data[team_games.TEAM_ID.category_name] == target_player_team_id)
        & (team_game_data[team_games.GAME_DATE.category_name] < target_game_date_str)
    ]

    if previous_team_games.empty:
        raise PredictionRefused(
            Refusal.NO_TEAM_HISTORY,
            f"Team {target_player_team_id} has no recorded game before {target_game_date_str}."
        )

    previous_game_data = previous_team_games.sort_values(
        by=team_games.GAME_DATE.category_name
    ).iloc[-1]
    previous_game_id = previous_game_data[team_games.GAME_ID.category_name]
    previous_team_id = previous_game_data[team_games.TEAM_ID.category_name]
    previous_game_team_player_ids: set[int] = set(
        player_game_data[
        (player_game_data[player_games.TEAM_ID.category_name] == previous_team_id)
        & (player_game_data[player_games.GAME_ID.category_name] == previous_game_id)
        ]
        [player_games.PLAYER_ID.category_name]
    )
    target_game_team_player_ids = (
        previous_game_team_player_ids.union(added_core_teammate_player_ids)
        .difference(removed_core_teammate_player_ids)
    )
    target_game_team_player_ids.add(target_player_id)

    # The placeholder game is given the id prefix of its season phase, which is how every other game
    # in the data says which phase it belongs to.
    target_game_placeholder_id = game_columns.SEASON_ENCODINGS[target_game.season_type.value]

    target_game_matchup: str = (
        game_columns.HOME_OR_AWAY_ENCODING[game_columns.HOME]
        if target_game.is_home(target_player_team_id)
        else game_columns.HOME_OR_AWAY_ENCODING[game_columns.AWAY]
    )

    if print_debug:
        print("Creating placeholder rows...")

    predicted_game_known_info_player_game_data_row: dict[str, Any] = {
        player_games.TEAM_ID.category_name : target_player_team_id,
        player_games.GAME_DATE.category_name : target_game_date_str,
        player_games.GAME_ID.category_name : target_game_placeholder_id,
        player_games.MINUTES_PLAYED.category_name : 1,
        player_games.MATCHUP.category_name : target_game_matchup
    }
    predicted_game_known_info_player_game_data_rows = []

    for player_id in target_game_team_player_ids:
        predicted_game_known_info_player_teammate_game_data_row = predicted_game_known_info_player_game_data_row.copy()
        predicted_game_known_info_player_teammate_game_data_row[player_games.PLAYER_ID.category_name] = player_id

        if player_id in added_core_teammate_player_ids:
            predicted_game_known_info_player_teammate_game_data_row[player_games.MINUTES_PLAYED.category_name] = game_columns.CORE_PLAYER_MINUTES_CUTOFF + 1

        predicted_game_known_info_player_game_data_rows.append(predicted_game_known_info_player_teammate_game_data_row)

    predicted_game_known_info_player_game_data = pd.DataFrame(predicted_game_known_info_player_game_data_rows)
    player_game_data = pd.concat([player_game_data, predicted_game_known_info_player_game_data], ignore_index=True)

    predicted_game_known_info_team_game_data_row = {
        team_games.TEAM_ID.category_name : target_player_team_id,
        team_games.GAME_DATE.category_name : target_game_date_str,
        team_games.GAME_ID.category_name : target_game_placeholder_id,
        team_games.MATCHUP.category_name : target_game_matchup
    }
    predicted_game_known_info_opponent_team_game_data_row = predicted_game_known_info_team_game_data_row.copy()
    predicted_game_known_info_opponent_team_game_data_row[team_games.TEAM_ID.category_name] = target_player_opponent_team_id
    predicted_game_known_info_team_game_data = pd.DataFrame(
        [predicted_game_known_info_team_game_data_row, predicted_game_known_info_opponent_team_game_data_row]
        )
    team_game_data = pd.concat([team_game_data, predicted_game_known_info_team_game_data], ignore_index=True)

    if print_debug:
        print("Processing data...")

    histories = _preprocess_game_data(features, player_info, player_game_data, team_game_data)
    history = histories.get(target_player_id)

    # _check_player_can_be_read covers why this happens, so reaching here means the build dropped the
    # player for a reason that check does not know about yet.
    if history is None:
        raise PredictionRefused(
            Refusal.TOO_FEW_GAMES,
            f"The feature build produced no games for player {target_player_id}."
        )

    target_indices = np.flatnonzero(history.game_ids == target_game_placeholder_id)
    if len(target_indices) != 1:
        raise ValueError(f"Expected exactly one placeholder game for player {target_player_id}, found {len(target_indices)}.")

    return (history, int(target_indices[0]))

def get_inference_data(
    features: FeatureSet,
    target_player_id: int,
    target_player_team_id: int,
    target_game: Game,
    removed_core_teammate_player_ids: Collection[int],
    added_core_teammate_player_ids: Collection[int],
    print_debug: bool = False
    ) -> tuple[PlayerGameSequences, SequenceInputSamples]:
    """
    Builds the input for one prediction: the target player's games and the single sample reading
    them. See _get_inference_player_game_data for what the target game arguments mean.
    """

    history, target_index = _get_inference_player_game_data(
        features,
        target_player_id,
        target_player_team_id,
        target_game,
        removed_core_teammate_player_ids,
        added_core_teammate_player_ids,
        print_debug
    )

    if print_debug:
        print("Creating input chunk...")

    static_input = history.static_input(target_index)

    # One sample reading the only player given, and no games belong to a training split.
    samples = SequenceInputSamples(
        np.zeros(1, dtype=np.int64),
        np.array([target_index], dtype=np.int64),
        history.opponent_team_ids[target_index : target_index + 1],
        static_input.reshape(1, -1),
        np.zeros(1, dtype=np.float64)
    )

    player_game_sequences = PlayerGameSequences(
        [history.sequence_values],
        [history.opponent_team_ids],
        np.zeros(1, dtype=np.int64)
    )

    if print_debug:
        print("Completed input data creation...")

    return (player_game_sequences, samples)
