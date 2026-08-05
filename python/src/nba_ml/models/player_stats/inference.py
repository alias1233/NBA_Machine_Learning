"""
Running a saved player prop model against an upcoming game.

This is the half that deploys. It never imports the trainer or the evaluation graphs.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Collection

import torch

from nba_ml.entities import Game
from nba_ml.machine_learning import datasets, serialization, trainer
from nba_ml.machine_learning.architectures.gru_feed_forward import GRUFeedForward
from nba_ml.models.player_stats import features as player_prop_features
from nba_ml.models.player_stats.specifications import (
    MAX_SEQUENCE_LENGTH,
    SEQUENCE_SCALER,
    STATIC_SCALER,
    ModelSpecification
)
from nba_ml.stores import player_games

@lru_cache(maxsize=None)
def _load(model_file: Path) -> tuple[GRUFeedForward, dict[str, Any]]:
    """
    Reads a model and its scalers off disk once and keeps them, so a service answering many requests
    pays for the read once. Predicting never writes to either.
    """

    parameters_dict = serialization.load_data_from_file(model_file)

    return (GRUFeedForward.load_from_saved_parameters_dict(parameters_dict), parameters_dict)

def team_of(player_id: int, game: Game) -> int:
    """
    Which of the game's two teams the player is on, taken from the last game they played before it.

    Raises:
        ValueError if the player has no recorded game, or last played for neither of these teams,
        which is what a trade the databases have not caught up with looks like.
    """

    team_id = player_games.latest_team_id(player_id, before=game.date)
    if team_id is None:
        raise ValueError(f"Player {player_id} has no recorded game before {game.date}.")

    if team_id not in (game.home_team_id, game.away_team_id):
        raise ValueError(
            f"Player {player_id} last played for team {team_id}, which is not in this game. "
            "Name their team outright if they have just moved."
        )

    return team_id

def predict(
    model_specs: ModelSpecification,
    target_player_id: int,
    target_game: Game,
    removed_core_teammate_player_ids: Collection[int] = (),
    added_core_teammate_player_ids: Collection[int] = (),
    target_player_team_id: int | None = None,
    print_debug: bool = True
    ) -> list[float]:
    """
    Returns the probability of every whole number outcome of the stat this model predicts, from the
    lowest class up.

    See features._get_inference_player_game_data for what the roster arguments mean.

    Args:
        target_player_team_id names the player's team outright. Leave it unset unless they have just
        moved and no game records it yet.
    """

    if target_player_team_id is None:
        target_player_team_id = team_of(target_player_id, target_game)

    model, parameters_dict = _load(model_specs.model_file())

    player_game_sequences, samples = player_prop_features.get_player_prop_inference_data(
        model_specs.get_feature_set(),
        target_player_id,
        target_player_team_id,
        target_game,
        removed_core_teammate_player_ids,
        added_core_teammate_player_ids,
        print_debug=print_debug
    )

    dataset = datasets.build_inference_dataset(
        player_game_sequences,
        samples,
        MAX_SEQUENCE_LENGTH,
        parameters_dict[SEQUENCE_SCALER],
        parameters_dict[STATIC_SCALER]
    )

    predictions = trainer.predict(
        model,
        dataset,
        collate_fn=datasets.collate_sequence_batch
    )

    predicted_probabilities = torch.softmax(predictions, 1)

    return predicted_probabilities.tolist()[0]
