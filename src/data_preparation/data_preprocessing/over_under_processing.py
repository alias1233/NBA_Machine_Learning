from datetime import datetime

from src.data_preparation.data_collection import data_query as query
from . import processing_helpers as processing

def get_over_under_input_output_data() -> list:
    player_info = query.get_all_players_info()
    player_game_data = query.get_all_player_game_data()
    team_game_data = query.get_all_team_game_data()

    player_game_data = processing.sort_by_date_players(player_game_data)
    player_game_data = processing.add_rest_column(player_game_data, sorted_by_game_date=True)
    player_game_data = processing.add_points_column(player_game_data)
    player_game_data = processing.add_rebounds_column(player_game_data)

    team_game_data = processing.sort_by_date_team(team_game_data)
    team_game_data = processing.add_possessions_column(team_game_data)
    team_game_data = processing.add_season_type_columns(team_game_data)
    team_game_data = processing.add_home_or_away_column(team_game_data)

    return []

