import pandas as pd
from datetime import datetime
from enum import Enum

from src.data_preparation.data_collection import data_query as query
from src.data_preparation.data_collection.databases import player_game_database, player_info_database, team_game_database
from src.data_preparation.data_preprocessing import nba_data_processing
from src.data_preparation.data_preprocessing import rolling_category
from src.data_preparation.data_preprocessing.rolling_category import RollingCategory

# TODO: Output a categorical distribution of a stat instead of the actual raw stat number and predict a probability of that stat
# TODO: Allow for choosing which stat to predict the probabilities on, and only predict one stat at a time

DUPLICATE_OPPONENT_MERGED_CATEGORIES = [
    team_game_database.GAME_DATE.category_name,
    team_game_database.WIN_LOSS.category_name,
    team_game_database.MATCHUP.category_name,
    team_game_database.MINUTES_PLAYED.category_name,
    nba_data_processing.HOME_OR_AWAY,
    nba_data_processing.PRESEASON,
    nba_data_processing.REGULAR_SEASON,
    nba_data_processing.PLAYOFFS,
    nba_data_processing.PLAY_IN
]

PRE_UNUSED_PLAYER_CATEGORIES = [
    player_game_database.MATCHUP.category_name,
    player_game_database.WIN_LOSS.category_name
]

DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES = [
    player_game_database.GAME_DATE.category_name
]

# STATS BY ATTRIBUTES: #
ATTRIBUTE_COLUMNS = nba_data_processing.ALL_POSITIONS

STAT_COLUMNS = [
    nba_data_processing.POINTS,
    nba_data_processing.REBOUNDS,
    player_game_database.ASSISTS.category_name
]
ALL_STATS_BY_ATTRIBUTE_COLUMNS = [stat + nba_data_processing.STATS_BASED_ON_ATTRIBUTE_SUFFIX + attribute for stat in STAT_COLUMNS for attribute in ATTRIBUTE_COLUMNS]

# ROLLING DATA: #
PAST_CAREER_ALLOWED_PREFIX = "PAST_CAREER_"
MEAN_PREFIX = "MEAN_"
STD_PREFIX = "STD_"
PAST_CAREER_STATS = [
    RollingCategory(
        PAST_CAREER_ALLOWED_PREFIX + MEAN_PREFIX + stat_column,
        stat_column,
        rolling_category.MEAN_FUNCTION,
    ) for stat_column in STAT_COLUMNS
] + [
    RollingCategory(
        PAST_CAREER_ALLOWED_PREFIX + STD_PREFIX + stat_column,
        stat_column,
        rolling_category.STD_FUNCTION,
    ) for stat_column in STAT_COLUMNS
]

ROLLING_WINDOW = 20

PAST_MEAN_ALLOWED_INFIX = "PAST_MEAN_ALLOWED_"
PAST_OPPONENT_ALLOWED_MEAN_STATS_BY_ATTRIBUTE_COLUMNS = [
    RollingCategory(
        nba_data_processing.OPPONENT_PREFIX + PAST_MEAN_ALLOWED_INFIX + stat_by_attribute_column,
        stat_by_attribute_column,
        rolling_category.MEAN_FUNCTION,
        ROLLING_WINDOW
        ) for stat_by_attribute_column in ALL_STATS_BY_ATTRIBUTE_COLUMNS
        ]

PLAYER_ROLLING_CATEGORIES = PAST_CAREER_STATS

TEAM_ROLLING_CATEGORIES = [] 

OPPONENT_TEAM_ROLLING_CATEGORIES = PAST_OPPONENT_ALLOWED_MEAN_STATS_BY_ATTRIBUTE_COLUMNS

# INPUT OUTPUT STRUCTURE: #
PAST_GAMES_PLAYED_SEQUENCE_LENGTH = 15
PAST_GAMES_PLAYED_AGAINST_OPPONENT_SEQUENCE_LENGTH = 3

INPUT_DATA_PLAYER_INFO = "PLAYER_INFO"
INPUT_DATA_PAST_GAMES_SEQUENCE = "PAST_GAMES_SEQUENCE"
INPUT_DATA_PAST_GAMES_AGAINST_OPPONENT_SEQUENCE = "PAST_GAMES_AGAINST_OPPONENT_SEQUENCE"
INPUT_DATA_STATIC_DATA = "STATIC_DATA"

# Players with less than this number of games will be removed from the dataset
MINIMUM_REQUIRED_GAMES_PLAYED = PAST_GAMES_PLAYED_SEQUENCE_LENGTH + 1

POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC = [
    player_info_database.PLAYER_ID.category_name,
    player_info_database.POSITION.category_name,
    player_info_database.FROM_YEAR.category_name,
    player_info_database.TO_YEAR.category_name,
    player_info_database.BIRTHDATE.category_name
]
POST_UNUSED_TRAINING_DATA_COLUMNS_SEQUENCE = [
    team_game_database.TEAM_ID.category_name, nba_data_processing.OPPONENT_PREFIX + team_game_database.TEAM_ID.category_name,
    team_game_database.GAME_DATE.category_name,
    team_game_database.GAME_ID.category_name,
    team_game_database.MATCHUP.category_name,
    team_game_database.WIN_LOSS.category_name,
    player_game_database.PLAYER_ID.category_name
] + (
    ALL_STATS_BY_ATTRIBUTE_COLUMNS
) + [
    nba_data_processing.OPPONENT_PREFIX + stat_by_attribute_column for stat_by_attribute_column in ALL_STATS_BY_ATTRIBUTE_COLUMNS
] + [
    career_stat.column_name for career_stat in PLAYER_ROLLING_CATEGORIES
]

INPUT_STATIC_GAME_DATA_COLUMNS = [
    nba_data_processing.REST,
    nba_data_processing.AGE_DURING_GAME,
    nba_data_processing.NBA_EXPERIENCE_DURING_GAME,
    nba_data_processing.PRESEASON,
    nba_data_processing.REGULAR_SEASON,
    nba_data_processing.PLAYOFFS,
    nba_data_processing.PLAY_IN,
    nba_data_processing.HOME_OR_AWAY
] + [
    category.column_name for category in PAST_OPPONENT_ALLOWED_MEAN_STATS_BY_ATTRIBUTE_COLUMNS
] + [
    career_stat.column_name for career_stat in PLAYER_ROLLING_CATEGORIES
]

class TargetStat(Enum):
    PLAYER_POINTS = nba_data_processing.POINTS + nba_data_processing.PLAYER_SUFFIX
    PLAYER_REBOUNDS = nba_data_processing.REBOUNDS + nba_data_processing.PLAYER_SUFFIX
    PLAYER_ASSISTS = player_game_database.ASSISTS.category_name + nba_data_processing.PLAYER_SUFFIX

def preprocess_game_data(
        player_info: pd.DataFrame,
        player_game_data: pd.DataFrame,
        team_game_data: pd.DataFrame,
        print_debug: bool = False
        ) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Returns a list of tuples containing: 
    (dataframe containing static information about a player,
      dataframe containing data for every game played by that corresponding player.)
    """

    if print_debug:
        print("Feature engineering isolated data...")

    player_info[player_info_database.BIRTHDATE.category_name] = pd.to_datetime(player_info[player_info_database.BIRTHDATE.category_name])
    player_info[player_info_database.FROM_YEAR.category_name] = pd.to_datetime(player_info[player_info_database.FROM_YEAR.category_name], format='%Y')
    player_info = nba_data_processing.convert_height_to_inches(
        player_info,
        player_info_database.HEIGHT.category_name
    )
    player_info = nba_data_processing.add_encoded_position_columns(
        player_info,
        player_info_database.POSITION.category_name
        )
    player_info = nba_data_processing.encode_undrafted(
        player_info,
        player_info_database.DRAFT_NUMBER.category_name
    )
    player_info = nba_data_processing.encode_unknown_weight(
        player_info,
        player_info_database.WEIGHT.category_name
    )

    player_game_data = player_game_data.drop(columns=PRE_UNUSED_PLAYER_CATEGORIES, errors='ignore')
    player_game_data[player_game_database.GAME_DATE.category_name] = pd.to_datetime(player_game_data[player_game_database.GAME_DATE.category_name])
    player_game_data = nba_data_processing.add_points_column(
        player_game_data, 
        player_game_database.FIELD_GOALS_MADE.category_name, 
        player_game_database.THREE_POINTERS_MADE.category_name, 
        player_game_database.FREE_THROWS_MADE.category_name
        )
    player_game_data = nba_data_processing.add_total_rebounds_column(
        player_game_data,
        player_game_database.OFFENSIVE_REBOUNDS.category_name,
        player_game_database.DEFENSIVE_REBOUNDS.category_name
        )
    player_game_data = nba_data_processing.add_age_during_game_column(
        player_game_data,
        player_info,
        player_info_database.PLAYER_ID.category_name,
        player_game_database.PLAYER_ID.category_name,
        player_info_database.BIRTHDATE.category_name,
        player_game_database.GAME_DATE.category_name
    )
    player_game_data = nba_data_processing.add_years_NBA_experience_during_game_column(
        player_game_data,
        player_info,
        player_info_database.PLAYER_ID.category_name,
        player_game_database.PLAYER_ID.category_name,
        player_info_database.FROM_YEAR.category_name,
        player_game_database.GAME_DATE.category_name
    )

    team_game_data[team_game_database.GAME_DATE.category_name] = pd.to_datetime(team_game_data[team_game_database.GAME_DATE.category_name])
    team_game_data = nba_data_processing.add_points_column(
        team_game_data,
        team_game_database.FIELD_GOALS_MADE.category_name, 
        team_game_database.THREE_POINTERS_MADE.category_name, 
        team_game_database.FREE_THROWS_MADE.category_name
        )
    team_game_data = nba_data_processing.add_total_rebounds_column(
        team_game_data,
        team_game_database.OFFENSIVE_REBOUNDS.category_name,
        team_game_database.DEFENSIVE_REBOUNDS.category_name
        )
    team_game_data = nba_data_processing.add_possessions_column(
        team_game_data,
        team_game_database.FIELD_GOALS_ATTEMPTED.category_name,
        team_game_database.FREE_THROWS_ATTEMPTED.category_name,
        team_game_database.OFFENSIVE_REBOUNDS.category_name,
        team_game_database.TURNOVERS.category_name
        )
    team_game_data = nba_data_processing.add_encoded_season_type_columns(
        team_game_data,
        team_game_database.GAME_ID.category_name
        )
    team_game_data = nba_data_processing.add_encoded_home_or_away_column(
        team_game_data,
        team_game_database.MATCHUP.category_name
        )
    team_game_data = nba_data_processing.encode_win_loss_column_as_integer(
        team_game_data,
        team_game_database.WIN_LOSS.category_name
    )
    team_game_data = nba_data_processing.add_total_player_stats_per_game_by_attribute(
        team_game_data,
        player_game_data,
        player_info,
        player_info_database.PLAYER_ID.category_name,
        player_game_database.PLAYER_ID.category_name,
        team_game_database.GAME_ID.category_name,
        team_game_database.TEAM_ID.category_name,
        ATTRIBUTE_COLUMNS,
        STAT_COLUMNS
    )
    team_game_data = nba_data_processing.add_opponent_stat_columns(
        team_game_data,
        team_game_database.GAME_ID.category_name,
        team_game_database.TEAM_ID.category_name,
        DUPLICATE_OPPONENT_MERGED_CATEGORIES
        )

    if print_debug:
        print("Feature engineering historical-context-dependant game data...")

    accumulator = []
    for _, game_data in team_game_data.groupby(by=team_game_database.TEAM_ID.category_name):
        game_data = game_data.sort_values(by=team_game_database.GAME_DATE.category_name)
        game_data = rolling_category.add_rolling_function_columns(game_data, TEAM_ROLLING_CATEGORIES)

        accumulator.append(game_data)
    
    team_game_data = pd.concat(accumulator)

    accumulator = []
    for _, game_data in team_game_data.groupby(by=nba_data_processing.OPPONENT_PREFIX + team_game_database.TEAM_ID.category_name):
        game_data = game_data.sort_values(by=team_game_database.GAME_DATE.category_name)
        game_data = rolling_category.add_rolling_function_columns(game_data, OPPONENT_TEAM_ROLLING_CATEGORIES)
        
        accumulator.append(game_data)
    
    team_game_data = pd.concat(accumulator)

    all_valid_players = player_info[player_info_database.PLAYER_ID.category_name].unique()
    accumulator = []
    for player_id, game_data in player_game_data.groupby(by=player_game_database.PLAYER_ID.category_name):
        if len(game_data) < MINIMUM_REQUIRED_GAMES_PLAYED or player_id not in all_valid_players:
            continue
        
        game_data = game_data.sort_values(by=player_game_database.GAME_DATE.category_name)
        game_data = nba_data_processing.add_rest_column(
            game_data,
            player_game_database.GAME_DATE.category_name
            )
        game_data = rolling_category.add_rolling_function_columns(game_data, PLAYER_ROLLING_CATEGORIES)

        accumulator.append(game_data)

    player_game_data = pd.concat(accumulator)

    if print_debug:
        print("Rearranging data...")

    player_info = nba_data_processing.sort_columns_alphabetically(player_info)
    static_player_info_dict = nba_data_processing.create_lookup_table(
        player_info,
        player_info_database.PLAYER_ID.category_name
    )
    
    player_team_game_data = nba_data_processing.merge_player_team_game_data(
        player_game_data,
        team_game_data,
        team_game_database.GAME_ID.category_name,
        player_game_database.GAME_ID.category_name,
        team_game_database.TEAM_ID.category_name,
        player_game_database.TEAM_ID.category_name,
        DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES
    )
    player_team_game_data = nba_data_processing.sort_columns_alphabetically(player_team_game_data)

    preprocessed_game_data = []
    for player_id, game_data in player_team_game_data.groupby(by=player_game_database.PLAYER_ID.category_name):
        game_data = game_data.sort_values(by=team_game_database.GAME_DATE.category_name)
        
        preprocessed_game_data.append((static_player_info_dict[player_id], game_data))

    if print_debug:
        print("Finished generating game data.")

    return preprocessed_game_data

def get_past_games_against_opponent(opponent_game_data: pd.DataFrame, date_of_game: datetime) -> pd.DataFrame | None:
    game_data_before_game_data = opponent_game_data[opponent_game_data[team_game_database.GAME_DATE.category_name] < date_of_game]
    
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

    all_player_info: pd.DataFrame = query.get_all_players_info()
    all_player_info = all_player_info.dropna()

    all_player_game_data: pd.DataFrame = query.get_all_player_game_data()
    all_player_game_data = all_player_game_data.dropna()

    all_team_game_data: pd.DataFrame = query.get_all_team_game_data()
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

    for player_data in data_per_player:
        static_player_info, player_game_data = player_data
        static_player_info = static_player_info.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_STATIC, errors='ignore')

        opponent_game_data_dict = nba_data_processing.create_lookup_table(
            player_game_data, 
            nba_data_processing.OPPONENT_PREFIX + team_game_database.TEAM_ID.category_name
        )

        for index in range(PAST_GAMES_PLAYED_SEQUENCE_LENGTH, len(player_game_data), chunk_step_size):
            current_game = player_game_data.iloc[index]

            # Creating sequence of last played games against the opponent of the current game
            opponent_team_id = current_game[nba_data_processing.OPPONENT_PREFIX + team_game_database.TEAM_ID.category_name]
            if opponent_team_id not in opponent_game_data_dict:
                continue
            date_of_game: datetime = current_game[team_game_database.GAME_DATE.category_name]
            past_games_against_opponent = get_past_games_against_opponent(opponent_game_data_dict[opponent_team_id], date_of_game)
            if past_games_against_opponent is None:
                continue
            past_games_against_opponent = past_games_against_opponent.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_SEQUENCE, errors='ignore')

            # Creating sequence of last played games by the current player 
            past_games_sequence = player_game_data.iloc[index - PAST_GAMES_PLAYED_SEQUENCE_LENGTH : index]
            past_games_sequence = past_games_sequence.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_SEQUENCE, errors='ignore')

            input_data_static_game_data = current_game[INPUT_STATIC_GAME_DATA_COLUMNS].to_frame().T

            output_data = current_game[[target_stat.value]].to_frame().T

            input_chunk = {
                INPUT_DATA_PLAYER_INFO : static_player_info,
                INPUT_DATA_PAST_GAMES_SEQUENCE : past_games_sequence,
                INPUT_DATA_PAST_GAMES_AGAINST_OPPONENT_SEQUENCE : past_games_against_opponent,
                INPUT_DATA_STATIC_DATA : input_data_static_game_data
            }
            output_chunk = output_data

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
        print("Finished data processing.")
    
    return (input_training_data, output_training_data, input_validation_data, output_validation_data, input_test_data, output_test_data)