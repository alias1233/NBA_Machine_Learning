"""
Running a saved game statistics model against an upcoming game.

A request names the game and nothing else, because neither side owns the answer. The sample is
anchored on the home team's row, which is what makes a positive point differential the home team's
margin.

This is the half that deploys. It never imports the trainer or the evaluation graphs.
"""

import torch

from nba_ml.entities import Game
from nba_ml.machine_learning import datasets, trainer
from nba_ml.models import loading
from nba_ml.models.game_stats import features
from nba_ml.models.game_stats.specifications import MAX_SEQUENCE_LENGTH, GameStatModelSpecification
from nba_ml.models.outputs import Prediction

def predict(
    model_specs: GameStatModelSpecification,
    target_game: Game,
    print_debug: bool = True
    ) -> Prediction:
    """
    Returns a probability for every position of this model's output, in that order, and how many
    earlier games the answer was built from.

    The count is the home team's, which is the side the answer is read off. Both sides had to clear
    the same floor for the game to be answerable at all.
    """

    model, parameters_dict = loading.load(model_specs.model_file())

    team_game_sequences, samples = features.get_inference_data(
        model_specs.get_feature_set(),
        target_game,
        print_debug=print_debug
    )

    dataset = datasets.build_inference_dataset(
        team_game_sequences,
        samples,
        MAX_SEQUENCE_LENGTH,
        parameters_dict[loading.SEQUENCE_SCALER],
        parameters_dict[loading.STATIC_SCALER]
    )

    predictions = trainer.predict(
        model,
        dataset,
        collate_fn=datasets.collate_sequence_batch
    )

    predicted_probabilities = torch.softmax(predictions, 1)

    return Prediction(
        values=predicted_probabilities.tolist()[0],
        past_games=int(samples.sequence_end_indices[0, 0])
    )
