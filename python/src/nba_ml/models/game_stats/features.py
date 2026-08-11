"""
Turning engineered team game rows into the samples a game statistics model reads.

A game statistic belongs to the game rather than to either side, so a game is one sample and not two.
Both sides still have to be read, so the sample reads both teams' past games and is anchored on the
home team's row. That is what makes a positive point differential the home team's margin, and it is
the only place in this family that says which side is which.

Reading the home row means home or away is the same for every sample, so it is left off the game
being predicted. It stays inside the sequences, where a team's past games are a mix of both.

The rows themselves, and the columns on them, are built in feature_engineering/team_game_rows.py and
shared with team statistics.
"""

from datetime import datetime

import pandas as pd

from nba_ml.entities import Game
from nba_ml.feature_engineering import game_columns, team_game_rows
from nba_ml.feature_engineering.samples import GameHistory, build_inference_sample, build_split_samples
from nba_ml.feature_engineering.team_game_rows import FeatureSet, TargetValue
from nba_ml.machine_learning.datasets import GameSequences, SequenceInputSamples
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.stores import team_games as team_game_store

SEQUENCES_READ = 2
"""
The home team's past games and the away team's, in that order.

Both sides decide a game, and neither was named, so both are read. A saved model has to agree with
this to be loadable, because a model fit on two histories cannot answer from one.
"""

def build_feature_set(target: TargetValue) -> FeatureSet:
    """
    Resolves the columns a model predicting the given value reads.

    Home or away comes off the game being predicted, because every sample is read off a home row and
    a column that never changes is capacity spent on nothing.
    """

    return team_game_rows.build_feature_set(target, dropped_static_columns=(game_columns.HOME_OR_AWAY,))

# TRAINING DATA: #
def get_all_labeled_data(
    features: FeatureSet,
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

    One sample per game, read off the home team's row and reading both teams' games.

    Returns:
        (games of every team, training samples, validation samples, test samples)
    """

    if print_debug:
        print("Querying data from databases...")

    all_team_game_data: pd.DataFrame = team_game_store.get_all_team_game_data().dropna()
    histories = team_game_rows.build_histories(
        features,
        all_team_game_data,
        sample_row_column=team_game_rows.IS_HOME_ROW,
        print_debug=print_debug
    )

    if print_debug:
        print("Arranging data into training chunks...")

    team_game_sequences, (training, validation, test) = build_split_samples(
        histories,
        (validation_split_start_date, test_split_start_date),
        team_game_rows.MINIMUM_PAST_GAMES,
        chunk_step_size,
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
    target_game: Game,
    print_debug: bool = False
    ) -> tuple[GameSequences, SequenceInputSamples]:
    """
    Builds the input for one prediction: both teams' games, and the single sample over them.

    The home team comes first, which is what makes the answer the home team's way round.

    Rest and break length come from the gap between the target game's date and each team's last
    recorded game. That is only their real rest while the database is current, so collect before
    predicting.
    """

    if print_debug:
        print("Querying data from databases...")

    team_game_data = team_game_rows.read_history_window(target_game)

    if print_debug:
        print("Creating placeholder rows...")

    team_game_data = pd.concat(
        [team_game_data, team_game_rows.placeholder_game_rows(target_game)],
        ignore_index=True
    )

    if print_debug:
        print("Processing data...")

    histories = team_game_rows.build_histories(features, team_game_data)

    if print_debug:
        print("Creating input chunk...")

    return build_inference_sample([
        _read_team(histories, team_id, target_game)
        for team_id in (target_game.home_team_id, target_game.away_team_id)
    ])
