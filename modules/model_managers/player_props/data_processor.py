import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from enum import Enum
from typing import Any

from modules.data_managers.team_game_data import team_game_data_manager
from modules.data_managers.player_game_data import player_game_data_manager
from modules.data_managers.player_info_data import player_info_manager
from src.data_preprocessing import nba_data_processing
from src.data_preprocessing import rolling_category
from src.data_preprocessing.rolling_category import RollingCategory
from src.data_preparation import nba_data_helpers

# TODO: Implement another model architecture such as transformmers or VAEs
# TODO: Add season time column, along with current team seed (?)
# TODO: Potentially use weighted averages that skew towards recent games for rolling data
# TODO: Potentially use per posession/minute stats instead of total?

ROLLING_WINDOW = 15
PAST_CAREER_MEAN_PREFIX = "PAST_CAREER_MEAN_"
PAST_CAREER_STD_PREFIX = "PAST_CAREER_STD_"
PAST_MEAN_PREFIX = "PAST_MEAN_"

DUPLICATE_OPPONENT_MERGED_CATEGORIES = [
    team_game_data_manager.GAME_DATE.category_name,
    team_game_data_manager.WIN_LOSS.category_name,
    team_game_data_manager.MATCHUP.category_name,
    team_game_data_manager.MINUTES_PLAYED.category_name,
    nba_data_processing.HOME_OR_AWAY,
    nba_data_processing.PRESEASON,
    nba_data_processing.REGULAR_SEASON,
    nba_data_processing.PLAYOFFS,
    nba_data_processing.PLAY_IN
]

PRE_UNUSED_PLAYER_CATEGORIES = [
    player_game_data_manager.MATCHUP.category_name,
    player_game_data_manager.WIN_LOSS.category_name
]

DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES = [
    player_game_data_manager.GAME_DATE.category_name
]

# PLAYER GAME FEATURE ENGINEERING: #
PAST_CAREER_CALCULATED_FROM_STATS_ALWAYS = [

]
past_career_calculated_from_stats = set()
def PAST_CAREER_STATS():
    return [
        RollingCategory(
            PAST_CAREER_MEAN_PREFIX + stat_column,
            stat_column,
            rolling_category.MEAN_FUNCTION,
        ) for stat_column in (
            PAST_CAREER_CALCULATED_FROM_STATS_ALWAYS +
            list(past_career_calculated_from_stats)
        )
    ] + [
        RollingCategory(
            PAST_CAREER_STD_PREFIX + stat_column,
            stat_column,
            rolling_category.STD_FUNCTION,
        ) for stat_column in (
            PAST_CAREER_CALCULATED_FROM_STATS_ALWAYS +
            list(past_career_calculated_from_stats)
        )
    ]

PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_ALWAYS = [

]
# TODO: Allow for each targeted stat to choose which attribute to get stats for
past_mean_player_stat_columns_to_be_used_for_past_mean_player_allowed_stats_by_attribute_over_mean = set()
def PAST_MEAN_PLAYER_STATS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN():
    return [
        RollingCategory(
            PAST_MEAN_PREFIX + stat,
            stat,
            rolling_category.MEAN_FUNCTION,
            ROLLING_WINDOW
        ) for stat in (
            PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_ALWAYS +
            list(past_mean_player_stat_columns_to_be_used_for_past_mean_player_allowed_stats_by_attribute_over_mean)
        )
    ]
def PAST_MEAN_PLAYER_STATS_OVER_MEAN_COLUMNS():
    return [
        (stat, past_mean_stat.column_name) 
        for stat, past_mean_stat 
        in zip(
            (
            PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_ALWAYS +
            list(past_mean_player_stat_columns_to_be_used_for_past_mean_player_allowed_stats_by_attribute_over_mean)
            ), 
            PAST_MEAN_PLAYER_STATS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN()
            )
    ]
def PAST_MEAN_PLAYER_STATS_OVER_MEAN():
    return nba_data_processing.get_all_differences_columns(PAST_MEAN_PLAYER_STATS_OVER_MEAN_COLUMNS())

ATTRIBUTE_COLUMNS = nba_data_processing.ALL_POSITIONS
def STAT_COLUMNS():
    return PAST_MEAN_PLAYER_STATS_OVER_MEAN()
def ALL_STATS_BY_ATTRIBUTE_COLUMNS():
    return nba_data_processing.get_all_stats_by_attribute_columns(
        ATTRIBUTE_COLUMNS,
        STAT_COLUMNS()
    )
HEIGHT_BOUNDARIES: list[float] = [
    75, 78, 80, 82
]
def ALL_STATS_BY_HEIGHT_BUCKET_COLUMNS():
    return nba_data_processing.get_all_stats_by_bucket_columns(
        player_info_manager.HEIGHT.category_name,
        HEIGHT_BOUNDARIES,
        STAT_COLUMNS()
    )
WEIGHT_BOUNDARIES: list[float] = [
    195, 215, 230, 245
]
def ALL_STATS_BY_WEIGHT_BUCKET_COLUMNS():
    return nba_data_processing.get_all_stats_by_bucket_columns(
        player_info_manager.WEIGHT.category_name,
        WEIGHT_BOUNDARIES,
        STAT_COLUMNS()
    )
def ALL_STATS_BY_ATTRIBUTE_AND_BUCKET_COLUMNS():
    return ALL_STATS_BY_ATTRIBUTE_COLUMNS() + ALL_STATS_BY_HEIGHT_BUCKET_COLUMNS() + ALL_STATS_BY_WEIGHT_BUCKET_COLUMNS()

# TEAM GAME FEATURE ENGINEERING: #
PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_ALWAYS = [
    team_game_data_manager.PERSONAL_FOULS.category_name
]
past_mean_team_stat_columns_to_be_used_for_past_mean_team_allowed_stats_over_mean = set()

def PAST_MEAN_TEAM_STATS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN():
    return [
        RollingCategory(
            PAST_MEAN_PREFIX + stat,
            stat,
            rolling_category.MEAN_FUNCTION,
            ROLLING_WINDOW
        ) for stat in (
            PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_ALWAYS +
            list(past_mean_team_stat_columns_to_be_used_for_past_mean_team_allowed_stats_over_mean)
        )
    ]
def PAST_MEAN_TEAM_STATS_OVER_MEAN_COLUMNS(): 
    return [
        (stat, past_mean_stat.column_name) 
        for stat, past_mean_stat 
        in zip(
            (
            PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_ALWAYS +
            list(past_mean_team_stat_columns_to_be_used_for_past_mean_team_allowed_stats_over_mean)
            ), 
            PAST_MEAN_TEAM_STATS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN()
            )
    ]
PAST_MEAN_ALLOWED_INFIX = "PAST_MEAN_ALLOWED_"
def PAST_MEAN_ALLOWED_STATS():
    return nba_data_processing.get_all_differences_columns(PAST_MEAN_TEAM_STATS_OVER_MEAN_COLUMNS())
def PAST_OPPONENT_ALLOWED_MEAN_STATS():
    return [
        RollingCategory(
            nba_data_processing.OPPONENT_PREFIX + PAST_MEAN_ALLOWED_INFIX + stat,
            stat,
            rolling_category.MEAN_FUNCTION,
            ROLLING_WINDOW
            ) for stat in PAST_MEAN_ALLOWED_STATS()
    ]
def PAST_OPPONENT_ALLOWED_MEAN_STATS_BY_ATTRIBUTE_COLUMNS():
    return [
        RollingCategory(
            nba_data_processing.OPPONENT_PREFIX + PAST_MEAN_ALLOWED_INFIX + stat_by_attribute_column,
            stat_by_attribute_column,
            rolling_category.MEAN_FUNCTION,
            ROLLING_WINDOW
            ) for stat_by_attribute_column in ALL_STATS_BY_ATTRIBUTE_AND_BUCKET_COLUMNS()
    ]

PAST_TEAM_STATS_ALWAYS = [
    nba_data_processing.POSSESSIONS, 
]
past_team_stats = set()
def PAST_MEAN_TEAM_STATS():
    return [
        RollingCategory(
            PAST_MEAN_PREFIX + stat,
            stat,
            rolling_category.MEAN_FUNCTION,
            ROLLING_WINDOW
        ) for stat in PAST_TEAM_STATS_ALWAYS + list(past_team_stats)
    ]

def PLAYER_ROLLING_CATEGORIES():
    return PAST_CAREER_STATS() + PAST_MEAN_PLAYER_STATS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN()

def TEAM_ROLLING_CATEGORIES():
    return PAST_MEAN_TEAM_STATS() + PAST_MEAN_TEAM_STATS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN()

def OPPONENT_TEAM_ROLLING_CATEGORIES():
    return PAST_OPPONENT_ALLOWED_MEAN_STATS() + PAST_OPPONENT_ALLOWED_MEAN_STATS_BY_ATTRIBUTE_COLUMNS()

# INPUT OUTPUT STRUCTURE: #
PAST_GAMES_PLAYED_SEQUENCE_LENGTH = 20
PAST_GAMES_PLAYED_AGAINST_OPPONENT_SEQUENCE_LENGTH = 3

INPUT_DATA_PLAYER_INFO = "PLAYER_INFO"
INPUT_DATA_PAST_GAMES_SEQUENCE = "PAST_GAMES_SEQUENCE"
INPUT_DATA_PAST_GAMES_AGAINST_OPPONENT_SEQUENCE = "PAST_GAMES_AGAINST_OPPONENT_SEQUENCE"
INPUT_DATA_STATIC_DATA = "STATIC_DATA"

OUTPUT = "OUTPUT"
output_columns = set()
def OUTPUT_COLUMNS():
    return list(output_columns)

# Players with less than this number of games will be removed from the dataset
MINIMUM_REQUIRED_GAMES_PLAYED = PAST_GAMES_PLAYED_SEQUENCE_LENGTH

STATS_TO_KEEP_SEQUENCE_ALWAYS = [
    player_game_data_manager.MINUTES_PLAYED.category_name + nba_data_processing.PLAYER_SUFFIX,
    nba_data_processing.POINTS + nba_data_processing.TEAM_SUFFIX, nba_data_processing.OPPONENT_PREFIX + nba_data_processing.POINTS,
    player_game_data_manager.PLUS_MINUS.category_name,
    player_game_data_manager.PERSONAL_FOULS.category_name + nba_data_processing.PLAYER_SUFFIX,
    nba_data_processing.HOME_OR_AWAY, nba_data_processing.LONG_BREAK, nba_data_processing.REST,
    nba_data_processing.CHANGED_TEAM,
    nba_data_processing.POSSESSIONS,
    team_game_data_manager.MINUTES_PLAYED.category_name + nba_data_processing.TEAM_SUFFIX,
    nba_data_processing.ROSTER_ADD_CORE_PLAYER, nba_data_processing.ROSTER_REMOVE_CORE_PLAYER
] + (
    nba_data_processing.ALL_SEASON_TYPES
)
stats_to_keep_sequence = set()
def STATS_TO_KEEP_SEQUENCE(): 
    stats = (
        STATS_TO_KEEP_SEQUENCE_ALWAYS + list(stats_to_keep_sequence)
    ) + [
        category.column_name for category in PAST_OPPONENT_ALLOWED_MEAN_STATS()
    ] + [
        nba_data_processing.OPPONENT_PREFIX + category.column_name for category in PAST_MEAN_TEAM_STATS()
    ]
    stats.sort()
    return stats
def STAT_TO_KEEP_PREV_OPPONENT_SEQUENCE():
    stats = STATS_TO_KEEP_SEQUENCE() + [
        nba_data_processing.DAYS_BEFORE_LAST_GAME
    ]
    stats.sort()
    return stats

STATS_TO_KEEP_STATIC_ALWAYS = [
        nba_data_processing.AGE_DURING_GAME, nba_data_processing.NBA_EXPERIENCE_DURING_GAME, 
        nba_data_processing.HOME_OR_AWAY, nba_data_processing.LONG_BREAK, nba_data_processing.REST,
        nba_data_processing.CHANGED_TEAM,
        nba_data_processing.ROSTER_ADD_CORE_PLAYER, nba_data_processing.ROSTER_REMOVE_CORE_PLAYER,
        nba_data_processing.DAYS_BEFORE_LAST_GAME
    ] + (
        nba_data_processing.ALL_SEASON_TYPES
    )
stats_to_keep_static = set()
def STATS_TO_KEEP_STATIC():
    stats = (
        STATS_TO_KEEP_STATIC_ALWAYS + list(stats_to_keep_static)
    ) + [
        category.column_name for category in OPPONENT_TEAM_ROLLING_CATEGORIES()
    ] + [
        category.column_name for category in PAST_CAREER_STATS()
    ] + [
        nba_data_processing.OPPONENT_PREFIX + category.column_name for category in PAST_MEAN_TEAM_STATS()
    ]
    stats.sort()
    return stats

POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC = [
    player_info_manager.PLAYER_ID.category_name,
    player_info_manager.POSITION.category_name,
    player_info_manager.FROM_YEAR.category_name,
    player_info_manager.TO_YEAR.category_name,
    player_info_manager.BIRTHDATE.category_name
]

class TargetStat(Enum):
    POINTS = nba_data_processing.POINTS + nba_data_processing.PLAYER_SUFFIX
    REBOUNDS = nba_data_processing.REBOUNDS + nba_data_processing.PLAYER_SUFFIX
    ASSISTS = player_game_data_manager.ASSISTS.category_name + nba_data_processing.PLAYER_SUFFIX

STATS_TO_KEEP_SEQUENCE_POINTS = [
    nba_data_processing.POINTS + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.OFFENSIVE_REBOUNDS.category_name + nba_data_processing.PLAYER_SUFFIX,
    team_game_data_manager.ASSISTS.category_name + nba_data_processing.TEAM_SUFFIX,
    player_game_data_manager.TURNOVERS.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FIELD_GOALS_MADE.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.THREE_POINTERS_ATTEMPTED.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.THREE_POINTERS_MADE.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FREE_THROWS_ATTEMPTED.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FREE_THROWS_MADE.category_name + nba_data_processing.PLAYER_SUFFIX,
]
PAST_TEAM_STATS_POINTS = [
    team_game_data_manager.BLOCKS.category_name
]
PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_POINTS = [
    nba_data_processing.POINTS,
    team_game_data_manager.TURNOVERS.category_name, 
    team_game_data_manager.OFFENSIVE_REBOUNDS.category_name, team_game_data_manager.ASSISTS.category_name,
    team_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name, team_game_data_manager.FIELD_GOALS_MADE.category_name,
    team_game_data_manager.THREE_POINTERS_ATTEMPTED.category_name, team_game_data_manager.THREE_POINTERS_MADE.category_name,
    team_game_data_manager.FREE_THROWS_ATTEMPTED.category_name,
]
PAST_CAREER_CALCULATED_FROM_STATS_POINTS = [
    nba_data_processing.POINTS
]
PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_POINTS = [
    nba_data_processing.POINTS
]

STATS_TO_KEEP_SEQUENCE_REBOUNDS = [
    player_game_data_manager.OFFENSIVE_REBOUNDS.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.DEFENSIVE_REBOUNDS.category_name + nba_data_processing.PLAYER_SUFFIX,
    team_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name + nba_data_processing.TEAM_SUFFIX,
    team_game_data_manager.FIELD_GOALS_MADE.category_name + nba_data_processing.TEAM_SUFFIX,
    team_game_data_manager.THREE_POINTERS_ATTEMPTED.category_name + nba_data_processing.TEAM_SUFFIX,
    team_game_data_manager.THREE_POINTERS_MADE.category_name + nba_data_processing.TEAM_SUFFIX,
]
PAST_TEAM_STATS_REBOUNDS = [
    
]
PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_REBOUNDS = [
    team_game_data_manager.OFFENSIVE_REBOUNDS.category_name,
    team_game_data_manager.DEFENSIVE_REBOUNDS.category_name,
    team_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name, team_game_data_manager.FIELD_GOALS_MADE.category_name, 
    team_game_data_manager.THREE_POINTERS_ATTEMPTED.category_name, team_game_data_manager.THREE_POINTERS_MADE.category_name
]
PAST_CAREER_CALCULATED_FROM_STATS_REBOUNDS = [
    player_game_data_manager.OFFENSIVE_REBOUNDS.category_name,
    player_game_data_manager.DEFENSIVE_REBOUNDS.category_name,
]
PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_REBOUNDS = [
    player_game_data_manager.OFFENSIVE_REBOUNDS.category_name,
    player_game_data_manager.DEFENSIVE_REBOUNDS.category_name,
]

STATS_TO_KEEP_SEQUENCE_ASSISTS = [
    player_game_data_manager.ASSISTS.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.TURNOVERS.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name + nba_data_processing.TEAM_SUFFIX,
    player_game_data_manager.FIELD_GOALS_MADE.category_name + nba_data_processing.TEAM_SUFFIX,
    player_game_data_manager.THREE_POINTERS_ATTEMPTED.category_name + nba_data_processing.TEAM_SUFFIX,
    player_game_data_manager.THREE_POINTERS_MADE.category_name + nba_data_processing.TEAM_SUFFIX
]
PAST_TEAM_STATS_ASSISTS = [
    team_game_data_manager.STEALS.category_name
]
PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_ASSISTS = [
    team_game_data_manager.ASSISTS.category_name,
    team_game_data_manager.TURNOVERS.category_name,
    team_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name, team_game_data_manager.FIELD_GOALS_MADE.category_name,
    team_game_data_manager.THREE_POINTERS_ATTEMPTED.category_name, team_game_data_manager.THREE_POINTERS_MADE.category_name,
]
PAST_CAREER_CALCULATED_FROM_STATS_ASSISTS = [
    player_game_data_manager.ASSISTS.category_name
]
PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_ASSISTS = [
    player_game_data_manager.ASSISTS.category_name
]

def _add_targeted_columns(
    target_stats: list[TargetStat]
    ):

    # Reset all columns to be empty
    stats_to_keep_sequence.clear()
    stats_to_keep_static.clear()
    past_team_stats.clear()
    past_mean_team_stat_columns_to_be_used_for_past_mean_team_allowed_stats_over_mean.clear()
    past_career_calculated_from_stats.clear()
    past_mean_player_stat_columns_to_be_used_for_past_mean_player_allowed_stats_by_attribute_over_mean.clear()
    output_columns.clear()

    # Add specific columns to the targeted columns based on the targeted stats
    def _add_other_columns_to_targeted_columns(
        stats_to_keep_sequence_other,
        stats_to_keep_static_other,
        past_team_stats_other,
        past_mean_team_stat_columns_to_be_used_for_past_mean_team_allowed_stats_over_mean_other,
        past_career_calculated_from_stats_other,
        past_mean_player_stat_columns_to_be_used_for_past_mean_player_allowed_stats_by_attribute_over_mean_other,
        output_column_other: str
        ):
        stats_to_keep_sequence.update(stats_to_keep_sequence_other)
        stats_to_keep_static.update(stats_to_keep_static_other)
        past_team_stats.update(past_team_stats_other)
        past_mean_team_stat_columns_to_be_used_for_past_mean_team_allowed_stats_over_mean.update(
            past_mean_team_stat_columns_to_be_used_for_past_mean_team_allowed_stats_over_mean_other
        )
        past_career_calculated_from_stats.update(past_career_calculated_from_stats_other)
        past_mean_player_stat_columns_to_be_used_for_past_mean_player_allowed_stats_by_attribute_over_mean.update(
            past_mean_player_stat_columns_to_be_used_for_past_mean_player_allowed_stats_by_attribute_over_mean_other
            )
        output_columns.add(output_column_other)

    for target_stat in set(target_stats):
        match target_stat:
            case TargetStat.POINTS:
                _add_other_columns_to_targeted_columns(
                    STATS_TO_KEEP_SEQUENCE_POINTS,
                    [],
                    PAST_TEAM_STATS_POINTS,
                    PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_POINTS,
                    PAST_CAREER_CALCULATED_FROM_STATS_POINTS,
                    PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_POINTS,
                    TargetStat.POINTS.value
                )
            case TargetStat.REBOUNDS:
                _add_other_columns_to_targeted_columns(
                    STATS_TO_KEEP_SEQUENCE_REBOUNDS,
                    [],
                    PAST_TEAM_STATS_REBOUNDS,
                    PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_REBOUNDS,
                    PAST_CAREER_CALCULATED_FROM_STATS_REBOUNDS,
                    PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_REBOUNDS,
                    TargetStat.REBOUNDS.value
                )
            case TargetStat.ASSISTS:
                _add_other_columns_to_targeted_columns(
                    STATS_TO_KEEP_SEQUENCE_ASSISTS,
                    [],
                    PAST_TEAM_STATS_ASSISTS,
                    PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN_ASSISTS,
                    PAST_CAREER_CALCULATED_FROM_STATS_ASSISTS,
                    PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN_ASSISTS,
                    TargetStat.ASSISTS.value
                )   

def _preprocess_game_data(
        player_info: pd.DataFrame,
        player_game_data: pd.DataFrame,
        team_game_data: pd.DataFrame,
        print_debug: bool = False
        ) -> dict[int, tuple[pd.DataFrame, pd.DataFrame, dict[int, pd.DataFrame]]]:
    """
    Returns a dict of tuples mapping each player id to: 
    (dataframe containing static information about the player,
      dataframe containing data for every game played by that corresponding player,
      dictionary mapping each opponent team's id to the games the corresponding player played against that team.)
    """

    if print_debug:
        print("Feature engineering player info data...")

    player_info[player_info_manager.BIRTHDATE.category_name] = pd.to_datetime(player_info[player_info_manager.BIRTHDATE.category_name])
    player_info[player_info_manager.FROM_YEAR.category_name] = pd.to_datetime(player_info[player_info_manager.FROM_YEAR.category_name], format='%Y')
    player_info = nba_data_processing.convert_height_to_inches(
        player_info,
        player_info_manager.HEIGHT.category_name,
        fill_unknown_with_mean=True
    )
    player_info = nba_data_processing.add_encoded_position_columns(
        player_info,
        player_info_manager.POSITION.category_name,
        fill_unknown_with_position=nba_data_processing.FORWARD
        )
    player_info = nba_data_processing.encode_undrafted(
        player_info,
        player_info_manager.DRAFT_NUMBER.category_name
    )
    player_info = nba_data_processing.handle_unknown_weight(
        player_info,
        player_info_manager.WEIGHT.category_name,
        fill_unknown_with_mean=True
    )

    if print_debug:
        print("Feature engineering player game data...")

    player_game_data = player_game_data.drop(columns=PRE_UNUSED_PLAYER_CATEGORIES, errors='ignore')
    player_game_data[player_game_data_manager.GAME_DATE.category_name] = pd.to_datetime(player_game_data[player_game_data_manager.GAME_DATE.category_name])
    player_game_data = nba_data_processing.add_points_column(
        player_game_data, 
        player_game_data_manager.FIELD_GOALS_MADE.category_name, 
        player_game_data_manager.THREE_POINTERS_MADE.category_name, 
        player_game_data_manager.FREE_THROWS_MADE.category_name
        )
    player_game_data = nba_data_processing.add_total_rebounds_column(
        player_game_data,
        player_game_data_manager.OFFENSIVE_REBOUNDS.category_name,
        player_game_data_manager.DEFENSIVE_REBOUNDS.category_name
        )
    player_game_data = nba_data_processing.add_age_during_game_column(
        player_game_data,
        player_info,
        player_info_manager.PLAYER_ID.category_name,
        player_game_data_manager.PLAYER_ID.category_name,
        player_info_manager.BIRTHDATE.category_name,
        player_game_data_manager.GAME_DATE.category_name
    )
    player_game_data = nba_data_processing.add_years_NBA_experience_during_game_column(
        player_game_data,
        player_info,
        player_info_manager.PLAYER_ID.category_name,
        player_game_data_manager.PLAYER_ID.category_name,
        player_info_manager.FROM_YEAR.category_name,
        player_game_data_manager.GAME_DATE.category_name
    )

    all_valid_players = player_info[player_info_manager.PLAYER_ID.category_name].unique()
    accumulator = []
    for player_id, game_data in player_game_data.groupby(by=player_game_data_manager.PLAYER_ID.category_name):
        if len(game_data) < MINIMUM_REQUIRED_GAMES_PLAYED or player_id not in all_valid_players:
            continue
        
        game_data = game_data.sort_values(by=player_game_data_manager.GAME_DATE.category_name)
        game_data = nba_data_processing.add_rest_and_long_break_columns(
            game_data,
            player_game_data_manager.GAME_DATE.category_name
            )
        game_data = nba_data_processing.add_changed_team_column(
            game_data,
            player_game_data_manager.TEAM_ID.category_name
        )
        game_data = rolling_category.add_rolling_function_columns(game_data, PLAYER_ROLLING_CATEGORIES())

        accumulator.append(game_data)
    player_game_data = pd.concat(accumulator)

    player_game_data = nba_data_processing.add_differences_columns(
        player_game_data,
        PAST_MEAN_PLAYER_STATS_OVER_MEAN_COLUMNS()
    )

    if print_debug:
        print("Feature engineering team game data...")

    team_game_data[team_game_data_manager.GAME_DATE.category_name] = pd.to_datetime(team_game_data[team_game_data_manager.GAME_DATE.category_name])
    team_game_data = nba_data_processing.add_points_column(
        team_game_data,
        team_game_data_manager.FIELD_GOALS_MADE.category_name, 
        team_game_data_manager.THREE_POINTERS_MADE.category_name, 
        team_game_data_manager.FREE_THROWS_MADE.category_name
        )
    team_game_data = nba_data_processing.add_total_rebounds_column(
        team_game_data,
        team_game_data_manager.OFFENSIVE_REBOUNDS.category_name,
        team_game_data_manager.DEFENSIVE_REBOUNDS.category_name
        )
    team_game_data = nba_data_processing.add_possessions_column(
        team_game_data,
        team_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name,
        team_game_data_manager.FREE_THROWS_ATTEMPTED.category_name,
        team_game_data_manager.OFFENSIVE_REBOUNDS.category_name,
        team_game_data_manager.TURNOVERS.category_name
        )
    team_game_data = nba_data_processing.add_encoded_season_type_columns(
        team_game_data,
        team_game_data_manager.GAME_ID.category_name
        )
    team_game_data = nba_data_processing.add_encoded_home_or_away_column(
        team_game_data,
        team_game_data_manager.MATCHUP.category_name
        )
    team_game_data = nba_data_processing.encode_win_loss_column_as_integer(
        team_game_data,
        team_game_data_manager.WIN_LOSS.category_name
    )
    team_game_data = nba_data_processing.add_total_player_stats_per_game_by_attribute(
        team_game_data,
        player_game_data,
        player_info,
        player_info_manager.PLAYER_ID.category_name,
        player_game_data_manager.PLAYER_ID.category_name,
        team_game_data_manager.GAME_ID.category_name,
        team_game_data_manager.TEAM_ID.category_name,
        ATTRIBUTE_COLUMNS,
        STAT_COLUMNS()
    )
    team_game_data = nba_data_processing.add_total_player_stats_per_game_by_bucket(
        team_game_data,
        player_game_data,
        player_info,
        player_info_manager.PLAYER_ID.category_name,
        player_game_data_manager.PLAYER_ID.category_name,
        team_game_data_manager.GAME_ID.category_name,
        team_game_data_manager.TEAM_ID.category_name,
        player_info_manager.HEIGHT.category_name,
        HEIGHT_BOUNDARIES,
        STAT_COLUMNS()
    )
    team_game_data = nba_data_processing.add_total_player_stats_per_game_by_bucket(
        team_game_data,
        player_game_data,
        player_info,
        player_info_manager.PLAYER_ID.category_name,
        player_game_data_manager.PLAYER_ID.category_name,
        team_game_data_manager.GAME_ID.category_name,
        team_game_data_manager.TEAM_ID.category_name,
        player_info_manager.WEIGHT.category_name,
        WEIGHT_BOUNDARIES,
        STAT_COLUMNS()
    )
    team_game_data = nba_data_processing.add_core_roster_change_columns(
        team_game_data,
        player_game_data,
        player_game_data_manager.PLAYER_ID.category_name,
        player_game_data_manager.GAME_ID.category_name,
        team_game_data_manager.GAME_ID.category_name,
        player_game_data_manager.TEAM_ID.category_name,
        team_game_data_manager.TEAM_ID.category_name,
        player_game_data_manager.MINUTES_PLAYED.category_name
    )

    accumulator = []
    for _, game_data in team_game_data.groupby(by=team_game_data_manager.TEAM_ID.category_name):
        game_data = game_data.sort_values(by=team_game_data_manager.GAME_DATE.category_name)
        game_data = rolling_category.add_rolling_function_columns(game_data, TEAM_ROLLING_CATEGORIES())

        accumulator.append(game_data)
    team_game_data = pd.concat(accumulator)

    team_game_data = nba_data_processing.add_opponent_stat_columns(
        team_game_data,
        team_game_data_manager.GAME_ID.category_name,
        team_game_data_manager.TEAM_ID.category_name,
        DUPLICATE_OPPONENT_MERGED_CATEGORIES
        )
    
    team_game_data = nba_data_processing.add_differences_columns(
        team_game_data,
        PAST_MEAN_TEAM_STATS_OVER_MEAN_COLUMNS()
    )

    accumulator = []
    for _, game_data in team_game_data.groupby(by=nba_data_processing.OPPONENT_PREFIX + team_game_data_manager.TEAM_ID.category_name):
        game_data = game_data.sort_values(by=team_game_data_manager.GAME_DATE.category_name)
        game_data = rolling_category.add_rolling_function_columns(game_data, OPPONENT_TEAM_ROLLING_CATEGORIES())
        
        accumulator.append(game_data)
    team_game_data = pd.concat(accumulator)

    if print_debug:
        print("Rearranging data...")

    player_info = nba_data_processing.sort_columns_alphabetically(player_info)
    static_player_info_dict = nba_data_processing.create_lookup_table(
        player_info,
        player_info_manager.PLAYER_ID.category_name
    )
    
    player_team_game_data = nba_data_processing.merge_player_team_game_data(
        player_game_data,
        team_game_data,
        team_game_data_manager.GAME_ID.category_name,
        player_game_data_manager.GAME_ID.category_name,
        team_game_data_manager.TEAM_ID.category_name,
        player_game_data_manager.TEAM_ID.category_name,
        DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES
    )
    player_team_game_data = nba_data_processing.sort_columns_alphabetically(player_team_game_data)

    # TODO: Potentially move this elsewhere so that resources are not wasted during inferencing by generating more data than needed

    # Creating output column which contains the targeted prediction value
    player_team_game_data[OUTPUT] = player_team_game_data[OUTPUT_COLUMNS()].sum(axis=1)

    preprocessed_game_data = {}
    for player_id, game_data in player_team_game_data.groupby(by=player_game_data_manager.PLAYER_ID.category_name):
        game_data = game_data.sort_values(by=team_game_data_manager.GAME_DATE.category_name)

        opponent_game_data_dict = {}
        for opponent_team_id, opponent_game_data in game_data.groupby(nba_data_processing.OPPONENT_PREFIX + team_game_data_manager.TEAM_ID.category_name):
            opponent_game_data = opponent_game_data.sort_values(by=team_game_data_manager.GAME_DATE.category_name)
            opponent_game_data = nba_data_processing.add_days_between_games_columns(
                opponent_game_data,
                team_game_data_manager.GAME_DATE.category_name
            )

            opponent_game_data_dict[opponent_team_id] = opponent_game_data
        
        preprocessed_game_data[player_id] = ((static_player_info_dict[player_id], game_data, opponent_game_data_dict))

    if print_debug:
        print("Finished generating game data.")

    return preprocessed_game_data

def _get_past_games_against_opponent(
    opponent_game_data: pd.DataFrame, 
    date_of_game: datetime
    ) -> tuple[pd.DataFrame, int] | None:
    """
    Creates a window of previous games against a specific opponent.

    Returns:
        None if there are not enough games to form the full window.
        Otherwise, return (dataframe containing the previous game data,
        days between most recent game against opponent and the current game)
    """

    game_data_before_and_including_current_game_data = opponent_game_data[opponent_game_data[team_game_data_manager.GAME_DATE.category_name] <= date_of_game]

    if len(game_data_before_and_including_current_game_data) - 1 < PAST_GAMES_PLAYED_AGAINST_OPPONENT_SEQUENCE_LENGTH:
        return None

    current_opponent_game_data = game_data_before_and_including_current_game_data.iloc[len(game_data_before_and_including_current_game_data) - 1]
    days_between_previous_game_against_current_opponent = current_opponent_game_data[nba_data_processing.DAYS_BEFORE_LAST_GAME]
    
    return (
        game_data_before_and_including_current_game_data.iloc[-PAST_GAMES_PLAYED_AGAINST_OPPONENT_SEQUENCE_LENGTH - 1 : -1],
        days_between_previous_game_against_current_opponent
    )

def _get_input_data_chunk(
        player_team_game_data: pd.DataFrame,
        opponent_game_data_dict: dict[int, pd.DataFrame],
        static_player_info: pd.DataFrame,
        current_game: pd.Series,
        date_of_game: datetime,
        index: int
    ) -> dict[str, pd.DataFrame] | None:

    current_game = current_game.copy()

    # Creating sequence of last played games against the opponent of the current game
    opponent_team_id = current_game[nba_data_processing.OPPONENT_PREFIX + team_game_data_manager.TEAM_ID.category_name]
    if opponent_team_id not in opponent_game_data_dict:
        return None
    opponent_game_data = opponent_game_data_dict[opponent_team_id]
    past_games_against_opponent_data = _get_past_games_against_opponent(opponent_game_data, date_of_game)
    if past_games_against_opponent_data is None:
        return None
    
    past_games_against_opponent, days_between_previous_game_against_current_opponent = past_games_against_opponent_data

    current_game[nba_data_processing.DAYS_BEFORE_LAST_GAME] = days_between_previous_game_against_current_opponent

    # Creating sequence of last played games by the current player 
    past_games_sequence = player_team_game_data.iloc[index - PAST_GAMES_PLAYED_SEQUENCE_LENGTH : index]

    past_games_sequence = past_games_sequence[STATS_TO_KEEP_SEQUENCE()]
    past_games_against_opponent = past_games_against_opponent[STAT_TO_KEEP_PREV_OPPONENT_SEQUENCE()]
    input_data_static_game_data = current_game[STATS_TO_KEEP_STATIC()].to_frame().T
    
    return {
        INPUT_DATA_PLAYER_INFO : static_player_info,
        INPUT_DATA_PAST_GAMES_SEQUENCE : past_games_sequence,
        INPUT_DATA_PAST_GAMES_AGAINST_OPPONENT_SEQUENCE : past_games_against_opponent,
        INPUT_DATA_STATIC_DATA : input_data_static_game_data
    }

def get_all_player_props_input_output_labeled_data(
        target_stats: list[TargetStat],
        validation_split_start_date: datetime,
        test_split_start_date: datetime,
        chunk_step_size: int = 1,
        print_debug: bool = False
        ) -> tuple[
            list[dict[str, pd.DataFrame]], 
            list[pd.DataFrame], 
            list[dict[str, pd.DataFrame]], 
            list[pd.DataFrame],
            list[dict[str, pd.DataFrame]], 
            list[pd.DataFrame]
            ]:
    """
    Returns a labeled training dataset for over/under prediction.

    The returned data is in the form of a tuple consisting of:
    (input training dataset, output training dataset, input validation data, output validation dataset, input test dataset, output test dataset)
    """

    _add_targeted_columns(target_stats)

    if print_debug:
        print("Querying data from databases...")

    all_player_info: pd.DataFrame = player_info_manager.get_all_players_info()
    all_player_info = all_player_info.dropna()

    all_player_game_data: pd.DataFrame = player_game_data_manager.get_all_player_game_data()
    all_player_game_data = all_player_game_data.dropna()

    all_team_game_data: pd.DataFrame = team_game_data_manager.get_all_team_game_data()
    all_team_game_data = all_team_game_data.dropna()

    data_per_player = _preprocess_game_data(all_player_info, all_player_game_data, all_team_game_data, print_debug)

    if print_debug:
        print("Arranging data into training chunks...")

    input_training_data: list[dict[str, pd.DataFrame]] = []
    output_training_data: list[pd.DataFrame] = []
    input_validation_data: list[dict[str, pd.DataFrame]] = []
    output_validation_data: list[pd.DataFrame] = []
    input_test_data: list[dict[str, pd.DataFrame]] = []
    output_test_data: list[pd.DataFrame] = []

    count: int = 0
    for _, player_data in data_per_player.items():
        static_player_info, player_team_game_data, opponent_game_data_dict = player_data
        static_player_info = static_player_info.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC, errors='ignore')

        for index in range(PAST_GAMES_PLAYED_SEQUENCE_LENGTH, len(player_team_game_data), chunk_step_size):
            current_game = player_team_game_data.iloc[index]
            date_of_game: datetime = current_game[team_game_data_manager.GAME_DATE.category_name]

            input_chunk = _get_input_data_chunk(
                player_team_game_data,
                opponent_game_data_dict,
                static_player_info,
                current_game,
                date_of_game,
                index
            )
            if input_chunk is None:
                continue
            output_chunk = current_game[[OUTPUT]].to_frame().T

            if print_debug:
                if count % 25000 == 0:
                    print(f"\r\033[KData Chunks Processed: {count}", end="", flush=True)
                count += 1

            # Separating chunks into validation, test, and training sets based on date cutoffs
            if date_of_game > test_split_start_date:
                input_test_data.append(input_chunk)
                output_test_data.append(output_chunk)
                continue

            if date_of_game > validation_split_start_date:
                input_validation_data.append(input_chunk)
                output_validation_data.append(output_chunk)
                continue

            input_training_data.append(input_chunk)
            output_training_data.append(output_chunk)
    
    if print_debug:
        print("")
        print("Finished data processing.")
    
    return (input_training_data, output_training_data, input_validation_data, output_validation_data, input_test_data, output_test_data)

def get_player_prop_inference_labeled_input_data(
    target_stats: list[TargetStat],
    target_player_id: int,
    target_player_team_id: int,
    target_player_opponent_team_id: int,
    target_game_date: datetime,
    target_game_season_type: nba_data_helpers.SeasonTypes,
    target_game_at_home: bool,
    target_player_removed_core_teammate_player_ids: set[int],
    target_player_added_core_teammate_player_ids: set[int],
    historical_window_length_years: int = 5,
    print_debug: bool = False
    ) -> dict[str, pd.DataFrame]:
    """
    Creates input data for a given target game for inferencing.

    Args:
        target_player_removed_core_teammate_player_ids hold a set of players who played more than 25 minutes in the previous game for the target team,
        and are not playing for the target game.

        target_player_added_core_teammate_player_ids hold a set of players who did not play in the previous game for the target team, but
        are now projected to play more than 25 minutes for the target game.
    """

    # TODO: Potentially refactor the process of encoding current known information into the input data

    _add_targeted_columns(target_stats)
    
    if print_debug:
        print("Querying data from databases...")

    historical_window_start_date: datetime = target_game_date - relativedelta(years=historical_window_length_years)

    player_info: pd.DataFrame = player_info_manager.get_player_info_after_year(historical_window_start_date.year)
    player_info = player_info.dropna()

    player_game_data: pd.DataFrame = player_game_data_manager.get_game_data_after_date(historical_window_start_date)
    player_game_data = player_game_data.dropna()

    team_game_data: pd.DataFrame = team_game_data_manager.get_game_data_after_date(historical_window_start_date)
    team_game_data = team_game_data.dropna()

    if print_debug:
        print("Getting previous game player ids...")
    
    # Get all player ids that played for the target team in the target team's most recent game.
    team_game_data_temp = team_game_data.copy()
    player_game_data_temp = player_game_data.copy()
    team_game_data_temp[team_game_data_manager.GAME_DATE.category_name] = pd.to_datetime(
            team_game_data_temp[team_game_data_manager.GAME_DATE.category_name]
            )
    previous_game_data = (
        team_game_data_temp[team_game_data_temp[team_game_data_manager.TEAM_ID.category_name] == target_player_team_id]
        .sort_values(by=team_game_data_manager.GAME_DATE.category_name, ascending=False)
        .iloc[0]
    )
    previous_game_id: int = previous_game_data[team_game_data_manager.GAME_ID.category_name]
    previous_team_id: int = previous_game_data[team_game_data_manager.TEAM_ID.category_name]
    previous_game_team_player_ids: set[int] = (
        player_game_data_temp[
        (player_game_data_temp[player_game_data_manager.TEAM_ID.category_name] == previous_team_id)
        & (player_game_data_temp[player_game_data_manager.GAME_ID.category_name] == previous_game_id)
        ]
        [player_game_data_manager.PLAYER_ID.category_name]
        .agg(set)
    )
    target_game_team_player_ids = (
        previous_game_team_player_ids.union(target_player_added_core_teammate_player_ids)
        .difference(target_player_removed_core_teammate_player_ids)
    )
    target_game_team_player_ids.add(target_player_id)

    match target_game_season_type:
        case nba_data_helpers.SeasonTypes.PRESEASON:
            season_type = nba_data_processing.PRESEASON
        case nba_data_helpers.SeasonTypes.REGULAR_SEASON:
            season_type = nba_data_processing.REGULAR_SEASON
        case nba_data_helpers.SeasonTypes.PLAYIN:
            season_type = nba_data_processing.PLAY_IN
        case nba_data_helpers.SeasonTypes.PLAYOFFS:
            season_type = nba_data_processing.PLAYOFFS

    target_game_placeholder_id = nba_data_processing.SEASON_ENCODINGS[season_type]

    target_game_date_str = nba_data_helpers.convert_datetime_to_str_nba_date_format(target_game_date)

    target_game_matchup: str = (
        nba_data_processing.HOME_OR_AWAY_ENCODING[nba_data_processing.HOME]
        if target_game_at_home
        else nba_data_processing.HOME_OR_AWAY_ENCODING[nba_data_processing.AWAY]
    )

    if print_debug:
        print("Creating placeholder rows...")

    predicted_game_known_info_player_game_data_row: dict[str, Any] = {
        player_game_data_manager.TEAM_ID.category_name : target_player_team_id,
        player_game_data_manager.GAME_DATE.category_name : target_game_date_str,
        player_game_data_manager.GAME_ID.category_name : target_game_placeholder_id,
        player_game_data_manager.MINUTES_PLAYED.category_name : 1,
        player_game_data_manager.MATCHUP.category_name : target_game_matchup
    }
    predicted_game_known_info_player_game_data_rows = []

    for player_id in target_game_team_player_ids:
        predicted_game_known_info_player_teammate_game_data_row = predicted_game_known_info_player_game_data_row.copy()
        predicted_game_known_info_player_teammate_game_data_row[player_game_data_manager.PLAYER_ID.category_name] = player_id

        if player_id in target_player_added_core_teammate_player_ids:
            predicted_game_known_info_player_teammate_game_data_row[player_game_data_manager.MINUTES_PLAYED.category_name] = nba_data_processing.CORE_PLAYER_MINUTES_CUTOFF + 1

        predicted_game_known_info_player_game_data_rows.append(predicted_game_known_info_player_teammate_game_data_row)

    predicted_game_known_info_player_game_data = pd.DataFrame(predicted_game_known_info_player_game_data_rows)
    player_game_data = pd.concat([player_game_data, predicted_game_known_info_player_game_data], ignore_index=True)

    predicted_game_known_info_team_game_data_row = {
        team_game_data_manager.TEAM_ID.category_name : target_player_team_id,
        team_game_data_manager.GAME_DATE.category_name : target_game_date_str,
        team_game_data_manager.GAME_ID.category_name : target_game_placeholder_id,
        team_game_data_manager.MATCHUP.category_name : target_game_matchup
    }
    predicted_game_known_info_opponent_team_game_data_row = predicted_game_known_info_team_game_data_row.copy()
    predicted_game_known_info_opponent_team_game_data_row[team_game_data_manager.TEAM_ID.category_name] = target_player_opponent_team_id
    predicted_game_known_info_team_game_data = pd.DataFrame(
        [predicted_game_known_info_team_game_data_row, predicted_game_known_info_opponent_team_game_data_row]
        )
    team_game_data = pd.concat([team_game_data, predicted_game_known_info_team_game_data], ignore_index=True)

    if print_debug:
        print("Processing data...")

    data_per_player = _preprocess_game_data(player_info, player_game_data, team_game_data)

    static_player_info, player_team_game_data, opponent_game_data_dict = data_per_player[target_player_id]

    # Get target game index in dataframe
    target_label = int(
        (player_team_game_data[team_game_data_manager.GAME_ID.category_name] == target_game_placeholder_id)
        .idxmax()
        )
    target_index = player_team_game_data.index.get_loc(target_label)
    if not isinstance(target_index, int):
        raise ValueError()

    static_player_info = static_player_info.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC, errors='ignore')

    if print_debug:
        print("Creating input chunk...")

    target_game = player_team_game_data.iloc[target_index]
    date_of_game: datetime = target_game[team_game_data_manager.GAME_DATE.category_name]

    input_data = _get_input_data_chunk(
        player_team_game_data,
        opponent_game_data_dict,
        static_player_info,
        target_game,
        date_of_game,
        target_index
    )

    if input_data is None:
        raise ValueError()
    
    if print_debug:
        print("Completed input data creation...")
    
    return input_data