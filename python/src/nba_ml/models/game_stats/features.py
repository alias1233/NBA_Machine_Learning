"""Builds training and inference samples for the game stats models."""

from datetime import datetime
from typing import Mapping

import pandas as pd

from nba_ml.entities import Game, RosterScenario
from nba_ml.feature_engineering import placeholders, season_columns, team_columns, team_game_rows
from nba_ml.feature_engineering.samples import (
    EvaluationSplit,
    GameHistory,
    build_inference_sample,
    build_split_samples,
    read_up_to
)
from nba_ml.feature_engineering.team_game_rows import FeatureSet, TargetValue
from nba_ml.machine_learning.datasets import GameSequences, SequenceInputSamples
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.stores import team_games as team_game_store

SEQUENCES_READ = 2
"""Number of sequences per sample: the home team's past games, then the away team's."""

def build_feature_set(target: TargetValue) -> FeatureSet:
    """Returns the feature set for a model predicting the given target."""

    return team_game_rows.build_feature_set(target, dropped_static_columns=(team_columns.HOME_OR_AWAY,))

# TRAINING DATA: #
def get_all_labeled_data(
    features: FeatureSet,
    training_start_date: datetime,
    evaluation_split: EvaluationSplit,
    chunk_step_size: int = 1,
    print_debug: bool = False
    ) -> tuple[
        GameSequences,
        SequenceInputSamples,
        SequenceInputSamples,
        SequenceInputSamples
        ]:
    """Builds every labeled sample, one per game, taken from the home team's row."""

    if print_debug:
        print("Querying data from databases...")

    all_team_game_data = season_columns.drop_incomplete_game_rows(
        team_game_store.get_all_team_game_data(),
        team_game_store.SEASON_TYPE.category_name
    )
    histories = team_game_rows.build_histories(
        features,
        all_team_game_data,
        team_game_rows.stored_roster_totals(all_team_game_data),
        sample_row_column=team_game_rows.IS_HOME_ROW,
        print_debug=print_debug
    )

    if print_debug:
        print("Arranging data into training chunks...")

    team_game_sequences, (training, validation, test) = build_split_samples(
        histories,
        evaluation_split,
        team_game_rows.MINIMUM_PAST_GAMES,
        chunk_step_size,
        sequence_columns=features.sequence_columns,
        static_columns=features.static_columns,
        training_start_date=training_start_date,
        read_opponent_history=True,
        print_debug=print_debug
    )

    if print_debug:
        print("Finished data processing.")

    return (team_game_sequences, training, validation, test)

# INFERENCE: #
def _read_team(
    histories: dict[int, GameHistory],
    team_id: int,
    target_game: Game
    ) -> tuple[GameHistory, int]:
    """Returns the team's history and the target game's index. Raises PredictionRefused if the team has too few games."""

    found = team_game_rows.find_target_game(histories, team_id, target_game)

    if found is None:
        raise PredictionRefused(
            Refusal.NO_TEAM_HISTORY,
            f"Team {team_id} has fewer than {team_game_rows.MINIMUM_PAST_GAMES} recorded games "
            f"before {target_game.date}, and a prediction reads at least that many."
        )

    return found

def get_inference_data(
    features: FeatureSet,
    target_game: Game,
    rosters: Mapping[int, RosterScenario],
    print_debug: bool = False
    ) -> tuple[GameSequences, SequenceInputSamples]:
    """Builds the input for one prediction from both teams' past games, home team first."""

    if print_debug:
        print("Querying data from databases...")

    team_game_data = team_game_rows.read_history_window(target_game)
    roster_totals = team_game_rows.prediction_roster_totals(target_game, rosters)

    if print_debug:
        print("Creating placeholder rows...")

    team_game_data = pd.concat(
        [team_game_data, placeholders.game_rows(target_game)],
        ignore_index=True
    )

    if print_debug:
        print("Processing data...")

    histories = team_game_rows.build_histories(features, team_game_data, roster_totals)

    if print_debug:
        print("Creating input chunk...")

    sides = [
        _read_team(histories, team_id, target_game)
        for team_id in (target_game.home_team_id, target_game.away_team_id)
    ]
    home_history, home_index = sides[0]

    return build_inference_sample(
        [read_up_to(history, index) for history, index in sides],
        home_history.static_input(home_index)
    )
