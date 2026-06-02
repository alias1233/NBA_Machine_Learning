from datetime import datetime

import data_collection.data_query as dqm
import data_preprocessing.processing_helpers as helpers

def get_input_data_cell(batch_length: int, player_id: int, opposing_team_id: int, game_date: datetime):
    """
    Returns the input data for a given player and game.
    """

