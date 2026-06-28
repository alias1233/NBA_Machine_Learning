import pandas as pd
from datetime import datetime
from enum import Enum

from modules.data_managers.team_game_data import team_game_data_manager
from modules.data_managers.player_game_data import player_game_data_manager
from modules.data_managers.player_info_data import player_info_manager
from src.data_preprocessing import nba_data_processing
from src.data_preprocessing import rolling_category
from src.data_preprocessing.rolling_category import RollingCategory

# TODO: Implement another model architecture such as transformmers or VAEs
# TODO: Add season time column, along with current team seed (?)

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
PAST_CAREER_CALCULATED_FROM_STATS = [
    nba_data_processing.POINTS
]
PAST_CAREER_STATS = [
    RollingCategory(
        PAST_CAREER_MEAN_PREFIX + stat_column,
        stat_column,
        rolling_category.MEAN_FUNCTION,
    ) for stat_column in PAST_CAREER_CALCULATED_FROM_STATS
] + [
    RollingCategory(
        PAST_CAREER_STD_PREFIX + stat_column,
        stat_column,
        rolling_category.STD_FUNCTION,
    ) for stat_column in PAST_CAREER_CALCULATED_FROM_STATS
]

PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN = [
    nba_data_processing.POINTS
]
PAST_MEAN_PLAYER_STATS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN = [
    RollingCategory(
        PAST_MEAN_PREFIX + stat,
        stat,
        rolling_category.MEAN_FUNCTION,
        ROLLING_WINDOW
    ) for stat in PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN
]
PAST_MEAN_PLAYER_STATS_OVER_MEAN_COLUMNS = [
    (stat, past_mean_stat.column_name) 
    for stat, past_mean_stat 
    in zip(PAST_MEAN_PLAYER_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN, PAST_MEAN_PLAYER_STATS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN)]
PAST_MEAN_PLAYER_STATS_OVER_MEAN = nba_data_processing.get_all_differences_columns(PAST_MEAN_PLAYER_STATS_OVER_MEAN_COLUMNS)

ATTRIBUTE_COLUMNS = nba_data_processing.ALL_POSITIONS
STAT_COLUMNS = PAST_MEAN_PLAYER_STATS_OVER_MEAN
ALL_STATS_BY_ATTRIBUTE_COLUMNS = nba_data_processing.get_all_stats_by_attribute_columns(
    ATTRIBUTE_COLUMNS,
    STAT_COLUMNS
)
HEIGHT_BOUNDARIES: list[float] = [
    75, 78, 80, 82
]
ALL_STATS_BY_HEIGHT_BUCKET_COLUMNS = nba_data_processing.get_all_stats_by_bucket_columns(
    player_info_manager.HEIGHT.category_name,
    HEIGHT_BOUNDARIES,
    STAT_COLUMNS
)
WEIGHT_BOUNDARIES: list[float] = [
    195, 215, 230, 245
]
ALL_STATS_BY_WEIGHT_BUCKET_COLUMNS = nba_data_processing.get_all_stats_by_bucket_columns(
    player_info_manager.WEIGHT.category_name,
    WEIGHT_BOUNDARIES,
    STAT_COLUMNS
)
ALL_STATS_BY_ATTRIBUTE_AND_BUCKET_COLUMNS = ALL_STATS_BY_ATTRIBUTE_COLUMNS + ALL_STATS_BY_HEIGHT_BUCKET_COLUMNS + ALL_STATS_BY_WEIGHT_BUCKET_COLUMNS

# TEAM GAME FEATURE ENGINEERING: #
PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN = [
    nba_data_processing.POINTS,
    team_game_data_manager.TURNOVERS.category_name, 
    team_game_data_manager.OFFENSIVE_REBOUNDS.category_name, team_game_data_manager.ASSISTS.category_name,
    team_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name, team_game_data_manager.FIELD_GOALS_MADE.category_name,
    team_game_data_manager.THREE_POINTERS_ATTEMPTED.category_name, team_game_data_manager.THREE_POINTERS_MADE.category_name,
    team_game_data_manager.FREE_THROWS_ATTEMPTED.category_name,
    team_game_data_manager.PERSONAL_FOULS.category_name
]
PAST_MEAN_TEAM_STATS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN = [
    RollingCategory(
        PAST_MEAN_PREFIX + stat,
        stat,
        rolling_category.MEAN_FUNCTION,
        ROLLING_WINDOW
    ) for stat in PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN
]
PAST_MEAN_TEAM_STATS_OVER_MEAN_COLUMNS = [
    (stat, past_mean_stat.column_name) 
    for stat, past_mean_stat 
    in zip(PAST_MEAN_TEAM_STAT_COLUMNS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN, PAST_MEAN_TEAM_STATS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN)]
PAST_MEAN_ALLOWED_INFIX = "PAST_MEAN_ALLOWED_"
PAST_MEAN_ALLOWED_STATS = nba_data_processing.get_all_differences_columns(PAST_MEAN_TEAM_STATS_OVER_MEAN_COLUMNS)
PAST_OPPONENT_ALLOWED_MEAN_STATS = [
    RollingCategory(
        nba_data_processing.OPPONENT_PREFIX + PAST_MEAN_ALLOWED_INFIX + stat,
        stat,
        rolling_category.MEAN_FUNCTION,
        ROLLING_WINDOW
        ) for stat in PAST_MEAN_ALLOWED_STATS
        ]
PAST_OPPONENT_ALLOWED_MEAN_STATS_BY_ATTRIBUTE_COLUMNS = [
    RollingCategory(
        nba_data_processing.OPPONENT_PREFIX + PAST_MEAN_ALLOWED_INFIX + stat_by_attribute_column,
        stat_by_attribute_column,
        rolling_category.MEAN_FUNCTION,
        ROLLING_WINDOW
        ) for stat_by_attribute_column in ALL_STATS_BY_ATTRIBUTE_AND_BUCKET_COLUMNS
        ]

PAST_TEAM_STATS = [
    nba_data_processing.POSSESSIONS, 
    team_game_data_manager.MINUTES_PLAYED.category_name,
    team_game_data_manager.STEALS.category_name, team_game_data_manager.BLOCKS.category_name
]
PAST_MEAN_TEAM_STATS = [
    RollingCategory(
        PAST_MEAN_PREFIX + stat,
        stat,
        rolling_category.MEAN_FUNCTION,
        ROLLING_WINDOW
    ) for stat in PAST_TEAM_STATS
]

PLAYER_ROLLING_CATEGORIES = PAST_CAREER_STATS + PAST_MEAN_PLAYER_STATS_TO_BE_USED_FOR_PAST_MEAN_PLAYER_ALLOWED_STATS_BY_ATTRIBUTE_OVER_MEAN

TEAM_ROLLING_CATEGORIES = PAST_MEAN_TEAM_STATS + PAST_MEAN_TEAM_STATS_TO_BE_USED_FOR_PAST_MEAN_TEAM_ALLOWED_STATS_OVER_MEAN

OPPONENT_TEAM_ROLLING_CATEGORIES = PAST_OPPONENT_ALLOWED_MEAN_STATS + PAST_OPPONENT_ALLOWED_MEAN_STATS_BY_ATTRIBUTE_COLUMNS

# INPUT OUTPUT STRUCTURE: #
PAST_GAMES_PLAYED_SEQUENCE_LENGTH = 20
PAST_GAMES_PLAYED_AGAINST_OPPONENT_SEQUENCE_LENGTH = 3

INPUT_DATA_PLAYER_INFO = "PLAYER_INFO"
INPUT_DATA_PAST_GAMES_SEQUENCE = "PAST_GAMES_SEQUENCE"
INPUT_DATA_PAST_GAMES_AGAINST_OPPONENT_SEQUENCE = "PAST_GAMES_AGAINST_OPPONENT_SEQUENCE"
INPUT_DATA_STATIC_DATA = "STATIC_DATA"

# Players with less than this number of games will be removed from the dataset
MINIMUM_REQUIRED_GAMES_PLAYED = PAST_GAMES_PLAYED_SEQUENCE_LENGTH

STAT_TO_KEEP_SEQUENCE = [
    nba_data_processing.POINTS + nba_data_processing.PLAYER_SUFFIX,
    nba_data_processing.POINTS + nba_data_processing.TEAM_SUFFIX, nba_data_processing.OPPONENT_PREFIX + nba_data_processing.POINTS,
    player_game_data_manager.MINUTES_PLAYED.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.PLUS_MINUS.category_name,
    player_game_data_manager.OFFENSIVE_REBOUNDS.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.PERSONAL_FOULS.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FIELD_GOALS_ATTEMPTED.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FIELD_GOALS_MADE.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.THREE_POINTERS_ATTEMPTED.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.THREE_POINTERS_MADE.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FREE_THROWS_ATTEMPTED.category_name + nba_data_processing.PLAYER_SUFFIX,
    player_game_data_manager.FREE_THROWS_MADE.category_name + nba_data_processing.PLAYER_SUFFIX,
    nba_data_processing.HOME_OR_AWAY, nba_data_processing.LONG_BREAK, nba_data_processing.REST,
    nba_data_processing.CHANGED_TEAM,
    nba_data_processing.POSSESSIONS,
    team_game_data_manager.MINUTES_PLAYED.category_name + nba_data_processing.TEAM_SUFFIX,
    nba_data_processing.ROSTER_ADD_CORE_PLAYER, nba_data_processing.ROSTER_REMOVE_CORE_PLAYER
] + (
    nba_data_processing.ALL_SEASONS
) + [
    category.column_name for category in PAST_OPPONENT_ALLOWED_MEAN_STATS
] + [
    nba_data_processing.OPPONENT_PREFIX + category.column_name for category in PAST_MEAN_TEAM_STATS
]
STAT_TO_KEEP_SEQUENCE.sort()

STAT_TO_KEEP_PREV_OPPONENT_SEQUENCE = STAT_TO_KEEP_SEQUENCE + [
    nba_data_processing.DAYS_BEFORE_LAST_GAME
]
STAT_TO_KEEP_PREV_OPPONENT_SEQUENCE.sort()

STATS_TO_KEEP_STATIC = [
    nba_data_processing.AGE_DURING_GAME, nba_data_processing.NBA_EXPERIENCE_DURING_GAME, 
    nba_data_processing.HOME_OR_AWAY, nba_data_processing.LONG_BREAK, nba_data_processing.REST,
    nba_data_processing.CHANGED_TEAM,
    nba_data_processing.ROSTER_ADD_CORE_PLAYER, nba_data_processing.ROSTER_REMOVE_CORE_PLAYER
] + (
    nba_data_processing.ALL_SEASONS
) + [
    category.column_name for category in OPPONENT_TEAM_ROLLING_CATEGORIES
] + [
    category.column_name for category in PAST_CAREER_STATS
] + [
    nba_data_processing.OPPONENT_PREFIX + category.column_name for category in PAST_MEAN_TEAM_STATS
]
STATS_TO_KEEP_STATIC.sort()

POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC = [
    player_info_manager.PLAYER_ID.category_name,
    player_info_manager.POSITION.category_name,
    player_info_manager.FROM_YEAR.category_name,
    player_info_manager.TO_YEAR.category_name,
    player_info_manager.BIRTHDATE.category_name
]

class TargetStat(Enum):
    PLAYER_POINTS = nba_data_processing.POINTS + nba_data_processing.PLAYER_SUFFIX
    PLAYER_REBOUNDS = nba_data_processing.REBOUNDS + nba_data_processing.PLAYER_SUFFIX
    PLAYER_ASSISTS = player_game_data_manager.ASSISTS.category_name + nba_data_processing.PLAYER_SUFFIX

def preprocess_game_data(
        player_info: pd.DataFrame,
        player_game_data: pd.DataFrame,
        team_game_data: pd.DataFrame,
        print_debug: bool = False
        ) -> list[tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]]:
    """
    Returns a list of tuples containing: 
    (dataframe containing static information about a player,
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
        game_data = rolling_category.add_rolling_function_columns(game_data, PLAYER_ROLLING_CATEGORIES)

        accumulator.append(game_data)
    player_game_data = pd.concat(accumulator)

    player_game_data = nba_data_processing.add_differences_columns(
        player_game_data,
        PAST_MEAN_PLAYER_STATS_OVER_MEAN_COLUMNS
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
        STAT_COLUMNS
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
        STAT_COLUMNS
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
        STAT_COLUMNS
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
        game_data = rolling_category.add_rolling_function_columns(game_data, TEAM_ROLLING_CATEGORIES)

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
        PAST_MEAN_TEAM_STATS_OVER_MEAN_COLUMNS
    )

    accumulator = []
    for _, game_data in team_game_data.groupby(by=nba_data_processing.OPPONENT_PREFIX + team_game_data_manager.TEAM_ID.category_name):
        game_data = game_data.sort_values(by=team_game_data_manager.GAME_DATE.category_name)
        game_data = rolling_category.add_rolling_function_columns(game_data, OPPONENT_TEAM_ROLLING_CATEGORIES)
        
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

    preprocessed_game_data = []
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
        
        preprocessed_game_data.append((static_player_info_dict[player_id], game_data, opponent_game_data_dict))

    if print_debug:
        print("Finished generating game data.")

    return preprocessed_game_data

def get_past_games_against_opponent(opponent_game_data: pd.DataFrame, date_of_game: datetime) -> pd.DataFrame | None:
    game_data_before_game_data = opponent_game_data[opponent_game_data[team_game_data_manager.GAME_DATE.category_name] < date_of_game]
    
    if len(game_data_before_game_data) < PAST_GAMES_PLAYED_AGAINST_OPPONENT_SEQUENCE_LENGTH:
        return None
    
    return game_data_before_game_data.iloc[-PAST_GAMES_PLAYED_AGAINST_OPPONENT_SEQUENCE_LENGTH:]

def get_all_player_props_input_output_labeled_data(
        target_stat: TargetStat,
        validation_split_start_date: datetime,
        test_split_start_date: datetime,
        chunk_step_size: int = 1,
        print_debug: bool = False
        ) -> tuple[list, list, list, list, list, list]:
    """
    Returns a labeled training dataset for over/under prediction.

    The returned data is in the form of a tuple consisting of:
    (input training dataset, output training dataset, input validation data, output validation dataset, input test dataset, output test dataset)
    """

    if print_debug:
        print("Querying data from databases...")

    all_player_info: pd.DataFrame = player_info_manager.get_all_players_info()
    all_player_info = all_player_info.dropna()

    all_player_game_data: pd.DataFrame = player_game_data_manager.get_all_player_game_data()
    all_player_game_data = all_player_game_data.dropna()

    all_team_game_data: pd.DataFrame = team_game_data_manager.get_all_team_game_data()
    all_team_game_data = all_team_game_data.dropna()

    data_per_player = preprocess_game_data(all_player_info, all_player_game_data, all_team_game_data, print_debug)

    if print_debug:
        print("Arranging data into training chunks...")

    input_training_data: list[dict[str, pd.DataFrame]] = []
    output_training_data: list[pd.DataFrame] = []
    input_validation_data: list[dict[str, pd.DataFrame]] = []
    output_validation_data: list[pd.DataFrame] = []
    input_test_data: list[dict[str, pd.DataFrame]] = []
    output_test_data: list[pd.DataFrame] = []

    count: int = 0
    for player_data in data_per_player:
        static_player_info, player_game_data, opponent_game_data_dict = player_data
        static_player_info = static_player_info.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC, errors='ignore')

        for index in range(PAST_GAMES_PLAYED_SEQUENCE_LENGTH, len(player_game_data), chunk_step_size):
            current_game = player_game_data.iloc[index]

            # Creating sequence of last played games against the opponent of the current game
            opponent_team_id = current_game[nba_data_processing.OPPONENT_PREFIX + team_game_data_manager.TEAM_ID.category_name]
            if opponent_team_id not in opponent_game_data_dict:
                continue
            date_of_game: datetime = current_game[team_game_data_manager.GAME_DATE.category_name]
            past_games_against_opponent = get_past_games_against_opponent(opponent_game_data_dict[opponent_team_id], date_of_game)
            if past_games_against_opponent is None:
                continue

            # Creating sequence of last played games by the current player 
            past_games_sequence = player_game_data.iloc[index - PAST_GAMES_PLAYED_SEQUENCE_LENGTH : index]

            past_games_sequence = past_games_sequence[STAT_TO_KEEP_SEQUENCE]
            past_games_against_opponent = past_games_against_opponent[STAT_TO_KEEP_PREV_OPPONENT_SEQUENCE]
            input_data_static_game_data = current_game[STATS_TO_KEEP_STATIC].to_frame().T # TODO: add days between games played for opponent game history

            output_data = current_game[[target_stat.value]].to_frame().T
            
            input_chunk = {
                INPUT_DATA_PLAYER_INFO : static_player_info,
                INPUT_DATA_PAST_GAMES_SEQUENCE : past_games_sequence,
                INPUT_DATA_PAST_GAMES_AGAINST_OPPONENT_SEQUENCE : past_games_against_opponent,
                INPUT_DATA_STATIC_DATA : input_data_static_game_data
            }
            output_chunk = output_data

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