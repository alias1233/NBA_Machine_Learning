"""Runs a trained player stats model on an upcoming game."""

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
    """Returns the player's team in the game, based on the last team they played for before it."""

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
    """Returns the predicted probability of each output class, in order."""

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

    return Prediction(
        values=predicted_probabilities.tolist()[0],
        past_games=int(samples.sequence_end_indices[0, 0])
    )
