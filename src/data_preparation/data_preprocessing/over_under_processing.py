from datetime import datetime

from src.data_preparation.data_collection import data_query as query
from . import processing_helpers as processing

def get_over_under_input_output_data(print_debug: bool = False) -> tuple:
    """
    Returns pre-processed training data for over/under prediction.

    The returned data is in the form of a tuple consisting of the input data at index 0, and the output data at index 1.
    """

    if print_debug:
        print("Querying data from databases...")

    player_info = query.get_all_players_info()
    player_info = player_info.dropna()
    player_game_data = query.get_all_player_game_data()
    player_game_data = player_game_data.dropna()
    team_game_data = query.get_all_team_game_data()
    team_game_data = team_game_data.dropna()

    if print_debug:
        print("Feature engineering player game data...")

    player_game_data = processing.sort_by_date_players(player_game_data)
    player_game_data = processing.add_rest_column(player_game_data, sorted_by_game_date=True)
    player_game_data = processing.add_points_column(player_game_data)
    player_game_data = processing.add_rebounds_column(player_game_data)

    if print_debug:
        print("Feature engineering team game data...")

    team_game_data = processing.sort_by_date_team(team_game_data)
    team_game_data = processing.add_points_column(team_game_data)
    team_game_data = processing.add_rebounds_column(team_game_data)
    team_game_data = processing.add_possessions_column(team_game_data)
    team_game_data = processing.add_season_type_columns(team_game_data)
    team_game_data = processing.add_home_or_away_column(team_game_data)

    if print_debug:
        print("Forming rolling averages...")

    # TODO: FINISH THIS

    # For each game to be sent for training, set the box score stats of that game as the output data.
    # For input data, first put in the player static details such as height, weight, position. 
    # Then, put in the last N1 games box score stats of the given player and the opposing team's opposing team averages over the last N2 games
    # Then, put in the last N3 opponent box score stats, along with their opposing team box score stats and the last N4 box score averages 
    
    return (player_game_data, team_game_data) # TEMP

