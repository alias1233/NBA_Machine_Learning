"""
Turning engineered team game rows into the samples a team statistics model reads.

A team statistic belongs to one side of a game, so a sample is one team in one game and both sides
of a game are samples. That is what makes this family's training set twice the size of the schedule
and why every row carries whether it was the home side.

The sequence a sample reads is the named team's own past games, and it reads the side it faces as
well when READS_OPPONENT_HISTORY says so. The rows themselves, and the columns on them, are built in
feature_engineering/team_game_rows.py and shared with game statistics.
"""

from datetime import datetime

import pandas as pd

from nba_ml.entities import Game
from nba_ml.feature_engineering import placeholders, season_columns, team_game_rows
from nba_ml.feature_engineering.samples import (
    GameHistory,
    build_inference_sample,
    build_split_samples,
    read_up_to
)
from nba_ml.feature_engineering.team_game_rows import FeatureSet, TargetValue
from nba_ml.machine_learning.datasets import GameSequences, SequenceInputSamples
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.stores import team_games as team_game_store

READS_OPPONENT_HISTORY = True
"""
Whether a sample reads the opposing team's past games beside the named team's.

The opponent's averages are already on the row either way, so this adds only the order those games
came in, and that order was worth about half a percent of the error when measured on 2026-08-11.
Turning it off changes what a sample holds without changing a column name, so a model fit one way
cannot answer the other. models/loading.py is what catches that.
"""

SEQUENCES_READ = 2 if READS_OPPONENT_HISTORY else 1
"""How many game histories one sample reads, which a saved model has to agree with to be loadable."""

def build_feature_set(target: TargetValue) -> FeatureSet:
    """Resolves the columns a model predicting the given value reads."""

    return team_game_rows.build_feature_set(target)

# TRAINING DATA: #
def get_all_labeled_data(
    features: FeatureSet,
    training_start_date: datetime,
    validation_split_start_date: datetime,
    test_split_start_date: datetime,
    chunk_step_size: int = 1,
    print_debug: bool = False
    ) -> tuple[
        GameSequences,
        SequenceInputSamples,
        SequenceInputSamples,
        SequenceInputSamples
        ]:
    """
    Builds every labeled sample the league holds, split into training, validation and test by date.

    Both sides of a game become a sample, one per team, because a model reads a game from the side it
    is asked about.

    Returns:
        (games of every team, training samples, validation samples, test samples)
    """

    if print_debug:
        print("Querying data from databases...")

    all_team_game_data = season_columns.drop_incomplete_game_rows(
        team_game_store.get_all_team_game_data(),
        team_game_store.SEASON_TYPE.category_name
    )
    histories = team_game_rows.build_histories(features, all_team_game_data, print_debug=print_debug)

    if print_debug:
        print("Arranging data into training chunks...")

    team_game_sequences, (training, validation, test) = build_split_samples(
        histories,
        (validation_split_start_date, test_split_start_date),
        team_game_rows.MINIMUM_PAST_GAMES,
        chunk_step_size,
        training_start_date=training_start_date,
        read_opponent_history=READS_OPPONENT_HISTORY,
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
    """One side of the predicted game, ready to be read, or a refusal naming the team it cannot."""

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
    target_team_id: int,
    target_game: Game,
    print_debug: bool = False
    ) -> tuple[GameSequences, SequenceInputSamples]:
    """
    Builds the input for one prediction: the games each side reads, and the single sample over them.

    Rest and break length come from the gap between the target game's date and each team's last
    recorded game. That is only their real rest while the database is current, so collect before
    predicting.

    Args:
        target_team_id is the side the answer belongs to, so its row is the static half of the input.
    """

    if print_debug:
        print("Querying data from databases...")

    team_game_data = team_game_rows.read_history_window(target_game)
    opponent_team_id = target_game.opponent_of(target_team_id)

    if print_debug:
        print("Creating placeholder rows...")

    team_game_data = pd.concat(
        [team_game_data, placeholders.game_rows(target_game)],
        ignore_index=True
    )

    if print_debug:
        print("Processing data...")

    histories = team_game_rows.build_histories(features, team_game_data)

    # Both sides are checked even where only the named one is read, because the row holds each side's
    # recent form and a team with nothing behind it reads as one averaging zero rather than as one
    # nothing is known about.
    sides = [
        _read_team(histories, team_id, target_game)
        for team_id in (target_team_id, opponent_team_id)
    ]

    if print_debug:
        print("Creating input chunk...")

    named_history, named_index = sides[0]

    return build_inference_sample(
        [
            read_up_to(history, index)
            for history, index in (sides if READS_OPPONENT_HISTORY else sides[:1])
        ],
        named_history.static_input(named_index)
    )
