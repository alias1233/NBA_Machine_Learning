from datetime import datetime
import torch
from sklearn.preprocessing import StandardScaler
import math

from . import data_processor
from . import train
from src.data_preprocessing import training_data_processing
from src.data_preparation import nba_data_helpers
from src.training import helpers
from src.training.model_architectures.feed_forward import FeedForward 

def predict(
    target_player_id: int,
    target_player_team_id: int,
    target_player_opponent_team_id: int,
    target_game_date: datetime,
    target_game_season_type: nba_data_helpers.SeasonTypes,
    target_game_at_home: bool,
    target_player_removed_core_teammate_player_ids: set[int],
    target_player_added_core_teammate_player_ids: set[int],
    ) -> list[float]:

    input_labeled = data_processor.get_player_prop_inference_labeled_input_data(
        train.TARGET_STAT,
        target_player_id,
        target_player_team_id,
        target_player_opponent_team_id,
        target_game_date,
        target_game_season_type,
        target_game_at_home,
        target_player_removed_core_teammate_player_ids,
        target_player_added_core_teammate_player_ids,
        print_debug=True
    )

    input_processed = training_data_processing.process_labeled_input(
        input_labeled,
        True
    )

    parameters_dict = helpers.load_data_from_file(train.SAVE_MODEL_FILE_PATH)
    model = FeedForward.load_from_saved_parameters_dict(
        parameters_dict
    )
    input_scaler: StandardScaler = parameters_dict[train.INPUT_SCALER]

    input_scaled = input_scaler.transform(input_processed)
    input: torch.Tensor = training_data_processing.to_tensor(input_scaled)

    model.eval()
    with torch.no_grad():
        predictions: torch.Tensor = model(input).cpu()

    predicted_probabilities = torch.softmax(predictions, 1)

    return predicted_probabilities.tolist()[0]

def calculate_odds_over_line(
    predicted_probabilities: list[float],
    over_under_line: float,
    minimum_value: int = 0
    ) -> float:
    """
    Calculates the probability given the probability distribution of a value to be higher than the
    given over_under_line.

    Args:
        predicted_probabilities is a list of floats where the value at each index represents the predicted probabilty of
        the value represented by that index of occuring. Each value is assumed to be ordered and in increments of exactly 1.

        over_under_line is a threshold set that a given value has a chance of exceeding.

        minimum_value is the value that the index at 0 of the predicted_probability represents.
    """

    above_line_threshold = math.ceil(over_under_line) - minimum_value

    probability_exceeds_over_under: float = 0.0
    for value in range(above_line_threshold, len(predicted_probabilities)):
        probability_exceeds_over_under += predicted_probabilities[value]

    return probability_exceeds_over_under