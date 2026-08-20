"""
Running a saved player game statistics model against an upcoming game.

This is the half that deploys. It never imports the trainer or the evaluation graphs.
"""

import torch

from nba_ml.entities import Game, RosterScenario
from nba_ml.machine_learning import datasets, trainer
from nba_ml.models import loading, requests
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.models.outputs import Prediction
from nba_ml.models.player_stats import features as stat_features
from nba_ml.models.player_stats.specifications import (
    MAX_SEQUENCE_LENGTH,
    PlayerStatModelSpecification
)
from nba_ml.stores import player_games

def team_of(player_id: int, game: Game) -> int:
    """
    Which of the game's two teams the player is on, taken from the last game they played before it.

    A player who has just moved last played for neither of these teams, and nothing stored says which
    one they joined, so the caller has to name it.

    Raises:
        PredictionRefused if the player has no recorded game, or last played for neither of these
        teams.
    """

    team_id = player_games.latest_team_id(player_id, before=game.date)
    if team_id is None:
        raise PredictionRefused(
            Refusal.UNKNOWN_PLAYER_TEAM,
            f"Player {player_id} has no recorded game before {game.date}."
        )

    if team_id not in (game.home_team_id, game.away_team_id):
        raise PredictionRefused(
            Refusal.UNKNOWN_PLAYER_TEAM,
            f"Player {player_id} last played for team {team_id}, which is not in this game. "
            "Name their team outright if they have just moved."
        )

    return team_id

def predict(
    model_specs: PlayerStatModelSpecification,
    target_player_id: int,
    target_game: Game,
    scenario: RosterScenario = RosterScenario(),
    target_player_team_id: int | None = None,
    print_debug: bool = True
    ) -> Prediction:
    """
    Returns a probability for every position of this model's output, in that order, and how many of
    the player's earlier games the answer was built from.

    Args:
        scenario is the change the request made to the player's team's last lineup. See
        features.build_target_game_row.
        target_player_team_id names the player's team outright. Leave it unset unless they have just
        moved and no game records it yet.

    Raises:
        PredictionRefused if the game has already been played, or if what is stored cannot answer.
    """

    requests.refuse_a_played_game(target_game)

    if target_player_team_id is None:
        target_player_team_id = team_of(target_player_id, target_game)

    model, parameters_dict = loading.load(model_specs.model_file())

    player_game_sequences, samples = stat_features.get_inference_data(
        model_specs.get_feature_set(),
        target_player_id,
        target_player_team_id,
        target_game,
        scenario,
        print_debug=print_debug
    )

    dataset = datasets.build_inference_dataset(
        player_game_sequences,
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

    # The sample reads every game behind the one being predicted, so where it stops is how many the
    # build found behind it.
    return Prediction(
        values=predicted_probabilities.tolist()[0],
        past_games=int(samples.sequence_end_indices[0, 0])
    )
