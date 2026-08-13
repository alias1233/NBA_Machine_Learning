"""
Running a saved team statistics model against an upcoming game.

A team statistic belongs to one side of the game, so a request names that side and the answer is
read off its row. It would be a different number for the other one.

This is the half that deploys. It never imports the trainer or the evaluation graphs.
"""

import torch

from nba_ml.entities import Game
from nba_ml.machine_learning import datasets, trainer
from nba_ml.models import loading, requests
from nba_ml.models.outputs import Prediction
from nba_ml.models.team_stats import features
from nba_ml.models.team_stats.specifications import MAX_SEQUENCE_LENGTH, TeamStatModelSpecification

def predict(
    model_specs: TeamStatModelSpecification,
    target_team_id: int,
    target_game: Game,
    print_debug: bool = True
    ) -> Prediction:
    """
    Returns a probability for every position of this model's output, in that order, and how many of
    the named team's earlier games the answer was built from.

    Args:
        target_team_id is the side of the game the answer belongs to.

    Raises:
        ValueError if the team is not playing in the given game.
        PredictionRefused if the game has already been played.
    """

    requests.refuse_a_played_game(target_game)

    model, parameters_dict = loading.load(model_specs.model_file())

    team_game_sequences, samples = features.get_inference_data(
        model_specs.get_feature_set(),
        target_team_id,
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

    # The named team's sequence reads every game up to the one being predicted, so where it stops is
    # how many the build found behind it.
    return Prediction(
        values=predicted_probabilities.tolist()[0],
        past_games=int(samples.sequence_end_indices[0, 0])
    )
