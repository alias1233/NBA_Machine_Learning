import pandas as pd
from pandas.core.window.rolling import Rolling

from src.data_preparation.data_collection import data_query as query
from src.data_preparation.data_collection.databases import player_game_database, player_info_database, team_game_database
from . import processing_helpers as processing
from .processing_helpers import RollingCategory

MEAN_STD_WINDOW = 20
PAST_POINTS_MEAN = RollingCategory("PAST_POINTS_MEAN", processing.POINTS.category_name, MEAN_STD_WINDOW, True, processing.MEAN_FUNCTION)
PAST_POINTS_STD = RollingCategory("PAST_POINTS_STD", processing.POINTS.category_name, MEAN_STD_WINDOW, True, processing.STD_FUNCTION)

PLAYER_ROLLING_CATEGORIES = [
    PAST_POINTS_MEAN,
    PAST_POINTS_STD
]

TEAM_ROLLING_CATEGORIES = [
    PAST_POINTS_MEAN,
    PAST_POINTS_STD
]

# Players with less than this number of games will be removed from the dataset.
MINIMUM_REQUIRED_GAMES_PLAYED = MEAN_STD_WINDOW + 1

def get_over_under_input_output_data(print_debug: bool = False) -> tuple:
    """
    Returns pre-processed training data for over/under prediction.

    The returned data is in the form of a tuple consisting of the input data at index 0, and the output data at index 1.
    """

    if print_debug:
        print("Querying data from databases...")

    player_info: pd.DataFrame = query.get_all_players_info()
    player_info = player_info.dropna()

    player_game_data: pd.DataFrame = query.get_all_player_game_data()
    player_game_data = player_game_data.dropna()

    team_game_data: pd.DataFrame = query.get_all_team_game_data()
    team_game_data = team_game_data.dropna()

    if print_debug:
        print("Feature engineering isolated data...")

    player_game_data = processing.add_points_column(player_game_data)
    player_game_data = processing.add_rebounds_column(player_game_data)

    team_game_data = processing.add_points_column(team_game_data)
    team_game_data = processing.add_rebounds_column(team_game_data)
    team_game_data = processing.add_possessions_column(team_game_data)
    team_game_data = processing.add_season_type_columns(team_game_data)
    team_game_data = processing.add_home_or_away_column(team_game_data)
    team_game_data = processing.add_opponent_stat_columns(team_game_data)

    if print_debug:
        print("Splitting data...")

    game_data_per_player: dict[str, pd.DataFrame] = processing.split_by_player(player_game_data)
    game_data_per_team: dict[str, pd.DataFrame] = processing.split_by_team(team_game_data)

    if print_debug:
        print("Feature engineering historical-context dependant data...")

    player_ids_to_remove = []
    for player_id, game_data in game_data_per_player.items():
        if len(game_data) < MINIMUM_REQUIRED_GAMES_PLAYED:
            player_ids_to_remove.append(player_id)
            continue

        game_data = processing.sort_games_by_date(game_data)

        game_data = processing.add_rest_column(game_data, True, True)
        game_data = processing.add_rolling_function_column(game_data, PLAYER_ROLLING_CATEGORIES)

        game_data_per_player[player_id] = game_data

    for id in player_ids_to_remove:
        game_data_per_player.pop(id)

    for team_id, game_data in game_data_per_team.items():
        game_data = processing.sort_games_by_date(game_data)

        game_data = processing.add_rolling_function_column(game_data, TEAM_ROLLING_CATEGORIES)

        game_data_per_team[team_id] = game_data

    if print_debug:
        print("Arranging data...")

    input_data = []
    output_data = []

    # TODO: FINISH THIS

    if print_debug:
        print("Finished data processing.")

    # For each game to be sent for training, set the box score stats of that game as the output data.
    # For input data, first put in the player static details such as height, weight, position. 
    # Then, put in the last N1 games box score stats of the given player and the opposing team's opposing team averages over the last N2 games
    # Then, put in the last N3 opponent box score stats, along with their opposing team box score stats and the last N4 box score averages 
    
    return (game_data_per_player, game_data_per_team) # TEMP

