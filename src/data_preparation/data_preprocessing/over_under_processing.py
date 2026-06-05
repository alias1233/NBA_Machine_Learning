from datetime import datetime

from src.data_preparation.data_collection import data_query
from . import processing_helpers

def get_input_data_cell(batch_length: int, player_id: int, opposing_team_id: int, game_date: datetime):
    """
    Returns the input data for a given player and game.
    """

