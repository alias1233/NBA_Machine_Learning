from datetime import datetime

from src.data_preparation.data_collection import data_query
from . import processing_helpers

def get_over_under_input_output_data(batch_length: int, player_id: int, opposing_team_id: int, game_date: datetime):
    """
    Returns the input data for a given player and game.
    """

