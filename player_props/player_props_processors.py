import pandas as pd
from datetime import datetime
import torch
from sklearn.preprocessing import StandardScaler

from src.data_preparation.data_collection import data_query as query
from src.data_preparation.data_collection.databases import player_game_database, player_info_database, team_game_database
from src.data_preparation.data_preprocessing import nba_data_processing
from src.data_preparation.data_preprocessing import rolling_category
from src.data_preparation.data_preprocessing.rolling_category import RollingCategory
from src.data_preparation.data_preprocessing import training_data_processing

MEAN_STD_WINDOW = 20
PAST_POINTS_MEAN = RollingCategory("PAST_POINTS_MEAN", nba_data_processing.POINTS, MEAN_STD_WINDOW, True, rolling_category.MEAN_FUNCTION)
PAST_POINTS_STD = RollingCategory("PAST_POINTS_STD", nba_data_processing.POINTS, MEAN_STD_WINDOW, True, rolling_category.STD_FUNCTION)

PLAYER_ROLLING_CATEGORIES = [

]

TEAM_ROLLING_CATEGORIES = [

]

# Players with less than this number of games will be removed from the dataset.
MINIMUM_REQUIRED_GAMES_PLAYED = MEAN_STD_WINDOW + 1

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

PLAYER_LABEL = "_PLAYER"
TEAM_LABEL = "_TEAM"

PRE_UNUSED_PLAYER_CATEGORIES = [
    player_game_database.MATCHUP.category_name,
    player_game_database.WIN_LOSS.category_name
]

DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES = [
    player_game_database.TEAM_ID.category_name,
    player_game_database.GAME_DATE.category_name,
]
REDUNDANT_MERGED_CATEGORIES = [column_name + PLAYER_LABEL for column_name in DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES]
RENAMING_MERGED_DICT = {column_name + TEAM_LABEL : column_name for column_name in DUPLICATE_PLAYER_TEAM_MERGED_CATEGORIES}

PAST_GAMES_PLAYED_SEQUENCE_LENGTH = 15
PAST_GAMES_PLAYED_AGAINST_OPPONENT_SEQUENCE_LENGTH = 4

INPUT_DATA_PLAYER_INFO = "PLAYER_INFO"
INPUT_DATA_PAST_GAMES_SEQUENCE = "PAST_GAMES_SEQUENCE"
INPUT_DATA_PAST_GAMES_AGAINST_OPPONENT_SEQUENCE = "PAST_GAMES_AGAINST_OPPONENT_SEQUENCE"
INPUT_DATA_STATIC_DATA = "STATIC_DATA"

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
]

OUTPUT_COLUMNS = [
    nba_data_processing.POINTS + PLAYER_LABEL,
    nba_data_processing.REBOUNDS + PLAYER_LABEL,
    player_game_database.ASSISTS.category_name + PLAYER_LABEL
]

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

    player_info = nba_data_processing.drop_all_rows_with_missing_info(player_info)
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
    team_game_data = nba_data_processing.add_opponent_stat_columns(
        team_game_data,
        team_game_database.GAME_ID.category_name,
        team_game_database.TEAM_ID.category_name,
        DUPLICATE_OPPONENT_MERGED_CATEGORIES
        )
    team_game_data = nba_data_processing.encode_win_loss_column_as_integer(
        team_game_data,
        team_game_database.WIN_LOSS.category_name
    )
    
    if print_debug:
        print("Creating processed player info lookup table...")

    player_info = player_info.sort_index(axis=1)
    static_player_info_dict = {}
    for player_id, player_info in player_info.groupby(by=player_info_database.PLAYER_ID.category_name):
        static_player_info_dict[player_id] = player_info

    if print_debug:
        print("Feature engineering historical-context-dependant game data...")

    accumulator = []
    for _, game_data in team_game_data.groupby(by=team_game_database.TEAM_ID.category_name):
        game_data = game_data.sort_values(by=team_game_database.GAME_DATE.category_name)
        game_data = rolling_category.add_rolling_function_columns(game_data, TEAM_ROLLING_CATEGORIES)

        accumulator.append(game_data)
    
    updated_team_game_data = pd.concat(accumulator)

    accumulator = []
    for player_id, game_data in player_game_data.groupby(by=player_game_database.PLAYER_ID.category_name):
        if len(game_data) < MINIMUM_REQUIRED_GAMES_PLAYED:
            continue
        if player_id not in static_player_info_dict:
            continue 
        
        game_data = game_data.sort_values(by=player_game_database.GAME_DATE.category_name)
        game_data = nba_data_processing.add_rest_column(
            game_data,
            player_game_database.GAME_DATE.category_name
            )
        game_data = rolling_category.add_rolling_function_columns(game_data, PLAYER_ROLLING_CATEGORIES)

        accumulator.append(game_data)

    updated_player_game_data = pd.concat(accumulator)

    if print_debug:
        print("Merging team game data and player game data...")
    
    player_team_game_data: pd.DataFrame = updated_player_game_data.merge(
        updated_team_game_data, 
        left_on=player_game_database.GAME_ID.category_name, 
        right_on=team_game_database.GAME_ID.category_name,
        suffixes=(PLAYER_LABEL, TEAM_LABEL)
        )
    player_team_game_data = player_team_game_data[
        player_team_game_data[player_game_database.TEAM_ID.category_name + PLAYER_LABEL] 
        == player_team_game_data[team_game_database.TEAM_ID.category_name + TEAM_LABEL]
        ]
    player_team_game_data = player_team_game_data.drop(columns=REDUNDANT_MERGED_CATEGORIES, errors='ignore')
    player_team_game_data = player_team_game_data.rename(columns=RENAMING_MERGED_DICT)

    if print_debug:
        print("Seperating game data by player and reformatting...")

    player_team_game_data = player_team_game_data.sort_index(axis=1)
    preprocessed_game_data = []
    for player_id, game_data in player_team_game_data.groupby(by=player_game_database.PLAYER_ID.category_name):
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
        validation_split_start_date: datetime,
        test_split_start_date: datetime,
        chunk_step_size: int = 1,
        print_debug: bool = False
        ) -> tuple:
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

        opponent_game_data_dict = {
            opponent_id : game_data 
            for opponent_id, game_data 
            in player_game_data.groupby(by=nba_data_processing.OPPONENT_PREFIX + team_game_database.TEAM_ID.category_name)
            }

        for index in range(PAST_GAMES_PLAYED_SEQUENCE_LENGTH, len(player_game_data), chunk_step_size):
            current_game = player_game_data.iloc[index]

            # Creating sequence of last played games against the opponent of the current game.
            opponent_team_id = current_game[nba_data_processing.OPPONENT_PREFIX + team_game_database.TEAM_ID.category_name]
            if opponent_team_id not in opponent_game_data_dict:
                continue
            date_of_game: datetime = current_game[team_game_database.GAME_DATE.category_name]
            past_games_against_opponent = get_past_games_against_opponent(opponent_game_data_dict[opponent_team_id], date_of_game)
            if past_games_against_opponent is None:
                continue
            past_games_against_opponent = past_games_against_opponent.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_SEQUENCE, errors='ignore')

            past_games_sequence = player_game_data.iloc[index - PAST_GAMES_PLAYED_SEQUENCE_LENGTH : index]
            past_games_sequence = past_games_sequence.drop(columns=POST_UNUSED_TRAINING_DATA_COLUMNS_SEQUENCE, errors='ignore')

            output_data = current_game[OUTPUT_COLUMNS].to_frame()
            input_data_static_game_data = current_game[INPUT_STATIC_GAME_DATA_COLUMNS].to_frame()

            input_chunk = {
                INPUT_DATA_PLAYER_INFO : static_player_info,
                INPUT_DATA_PAST_GAMES_SEQUENCE : past_games_sequence,
                INPUT_DATA_PAST_GAMES_AGAINST_OPPONENT_SEQUENCE : past_games_against_opponent,
                INPUT_DATA_STATIC_DATA : input_data_static_game_data
            }
            output_chunk = output_data

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

def get_all_player_props_input_output_training_data(
        validation_split_start_date: datetime,
        test_split_start_date: datetime,
        flatten: bool,
        chunk_step_size: int = 1,
        print_debug: bool = False
        ) -> tuple[
        torch.Tensor, torch.Tensor,
        torch.Tensor, torch.Tensor,
        torch.Tensor, torch.Tensor,
        StandardScaler, StandardScaler,
        ]:
    """
    Returns pre-processed training dataset for over/under prediction.

    The returned data is in the form of a tuple consisting of:
    (input training dataset, output training dataset, 
    input validation data, output validation dataset, 
    input test dataset, output test dataset, 
    input scaler, output scaler)
    """

    datasets = get_all_player_props_input_output_labeled_data(
        validation_split_start_date,
        test_split_start_date,
        chunk_step_size,
        print_debug
    )

    return training_data_processing.process_raw_data_for_training(*datasets, flatten=flatten)

