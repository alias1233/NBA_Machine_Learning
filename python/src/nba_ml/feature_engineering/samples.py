"""Turns engineered feature rows into training and inference samples."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from nba_ml.machine_learning.datasets import GameSequences, SequenceInputSamples

OUTPUT = "OUTPUT"
"""Name of the column with the target value."""

TRAINING_SPLIT = 0
VALIDATION_SPLIT = 1
TEST_SPLIT = 2
SPLIT_NAMES = ("training", "validation", "test")
"""Split names, in the order build_split_samples returns them."""

class SplitKey(StrEnum):
    """The key used to split evaluation samples into validation and test."""

    SUBJECT = "subject"
    """Split by subject, so a player or team is never in both splits."""

    GAME = "game"
    """Split by game, so both rows of a game are in the same split."""

@dataclass(frozen=True)
class EvaluationSplit():
    """Settings for which games are held out and how they are divided into validation and test."""

    start_date: datetime
    """First day of the evaluation period. Earlier games are used for training."""

    validation_fraction: float = 0.5

    split_on: SplitKey = SplitKey.SUBJECT
    seed: int = 0

    def __post_init__(self):
        if not 0.0 <= self.validation_fraction <= 1.0:
            raise ValueError(
                f"A validation fraction is a share of the evaluation period. Got {self.validation_fraction}."
            )

    def _share_of(self, key: int) -> float:
        """Hashes a key to a number between 0 and 1. The same key and seed always give the same number."""

        digest = hashlib.blake2b(f"{self.seed}:{key}".encode(), digest_size=8).digest()

        return int.from_bytes(digest, "big") / float(1 << 64)

    def split_of(self, key: int) -> int:
        return VALIDATION_SPLIT if self._share_of(key) < self.validation_fraction else TEST_SPLIT

    def splits_of(
        self,
        subject_id: int,
        game_ids: np.ndarray,
        game_dates: np.ndarray
        ) -> np.ndarray:
        """Returns the split of each of a subject's games, in the given order."""

        splits = np.full(len(game_dates), TRAINING_SPLIT, dtype=np.int64)
        evaluated = np.flatnonzero(game_dates >= np.datetime64(self.start_date))

        if len(evaluated) == 0:
            return splits

        if self.split_on is SplitKey.SUBJECT:
            splits[evaluated] = self.split_of(subject_id)
        else:
            splits[evaluated] = [self.split_of(int(game_id)) for game_id in game_ids[evaluated]]

        return splits

@dataclass(frozen=True)
class GameHistory():
    """The feature values of one subject's games, sorted oldest first."""

    static_subject_values: np.ndarray
    """Features of the subject that are the same for every game. Shape: (subject features,)."""

    game_ids: np.ndarray
    game_dates: np.ndarray
    sequence_values: np.ndarray
    """Shape: (games, sequence features)."""

    static_values: np.ndarray
    """Shape: (games, static features)."""

    opponent_team_ids: np.ndarray
    outputs: np.ndarray

    is_sample_row: np.ndarray
    """Whether each game can be used as a sample."""

    @property
    def game_count(self) -> int:
        return len(self.game_dates)

    def static_input(self, index: int) -> np.ndarray:
        """Returns the static input for the game at the given index."""

        return np.concatenate((self.static_subject_values, self.static_values[index]))

    def starting_on(self, start_date: datetime) -> "GameHistory":
        start = int(np.searchsorted(self.game_dates, np.datetime64(start_date), side="left"))
        return GameHistory(
            self.static_subject_values,
            self.game_ids[start:],
            self.game_dates[start:],
            self.sequence_values[start:],
            self.static_values[start:],
            self.opponent_team_ids[start:],
            self.outputs[start:],
            self.is_sample_row[start:]
        )

NO_STATIC_SUBJECT_VALUES = np.empty(0, dtype=np.float32)

def check_columns_are_finite(values: np.ndarray, columns: Sequence[str], described: str):
    non_finite = (~np.isfinite(values)).sum(axis=0)
    named = [f"{column} ({count:,} rows)" for column, count in zip(columns, non_finite) if count]

    if named:
        raise ValueError(
            f"The {described} hold values a model cannot read, so the build is unusable: "
            + ", ".join(named)
        )

def split_into_histories(
    game_data: pd.DataFrame,
    subject_id_column: str,
    game_id_column: str,
    game_date_column: str,
    opponent_team_id_column: str,
    sequence_columns: list[str],
    static_columns: list[str],
    static_subject_values: Mapping[int, np.ndarray] | None = None,
    sample_row_column: str | None = None
    ) -> dict[int, GameHistory]:
    """Splits a feature dataframe into one GameHistory per subject. It must be sorted by subject, then date."""

    game_ids = game_data[game_id_column].to_numpy()
    game_dates = game_data[game_date_column].to_numpy()
    sequence_values = game_data[sequence_columns].to_numpy(dtype=np.float32)
    static_values = game_data[static_columns].to_numpy(dtype=np.float32)
    opponent_team_ids = game_data[opponent_team_id_column].to_numpy(dtype=np.int64)
    outputs = game_data[OUTPUT].to_numpy(dtype=np.float64)
    is_sample_row = (
        np.ones(len(game_data), dtype=bool) if sample_row_column is None
        else game_data[sample_row_column].to_numpy(dtype=bool)
    )

    histories: dict[int, GameHistory] = {}
    for subject_id, positions in game_data.groupby(by=subject_id_column, sort=False).indices.items():
        subject_id = int(subject_id)
        start, stop = int(positions[0]), int(positions[-1]) + 1

        if stop - start != len(positions):
            raise ValueError(
                f"Every game of {subject_id_column} must sit together, so the frame has to be sorted by it first."
            )

        histories[subject_id] = GameHistory(
            static_subject_values=(
                NO_STATIC_SUBJECT_VALUES if static_subject_values is None
                else static_subject_values[subject_id]
            ),
            game_ids=game_ids[start:stop],
            game_dates=game_dates[start:stop],
            sequence_values=sequence_values[start:stop],
            static_values=static_values[start:stop],
            opponent_team_ids=opponent_team_ids[start:stop],
            outputs=outputs[start:stop],
            is_sample_row=is_sample_row[start:stop]
        )

    return histories

@dataclass(frozen=True)
class SequenceRead():
    """Points a sample to one subject's history and the index where its past games end."""

    sequence_index: int

    end_index: int
    """Index of the predicted game. The sample uses the games before it."""

    opponent_team_id: int
    """ID of the team this subject plays in the predicted game."""

class _SampleAccumulator():
    def __init__(self):
        self.sequence_indices: list[list[int]] = []
        self.sequence_end_indices: list[list[int]] = []
        self.opponent_team_ids: list[list[int]] = []
        self.static_inputs: list[np.ndarray] = []
        self.outputs: list[float] = []
        self.game_dates: list[np.datetime64] = []

    def add(
        self,
        reads: Sequence[SequenceRead],
        static_input: np.ndarray,
        output: float,
        game_date: np.datetime64
        ):
        self.sequence_indices.append([read.sequence_index for read in reads])
        self.sequence_end_indices.append([read.end_index for read in reads])
        self.opponent_team_ids.append([read.opponent_team_id for read in reads])
        self.static_inputs.append(static_input)
        self.outputs.append(output)
        self.game_dates.append(game_date)

    def to_samples(self, static_input_dim: int, sequence_count: int) -> SequenceInputSamples:
        def indices(values: list[list[int]]) -> np.ndarray:
            return (
                np.array(values, dtype=np.int64) if values
                else np.empty((0, sequence_count), dtype=np.int64)
            )

        return SequenceInputSamples(
            indices(self.sequence_indices),
            indices(self.sequence_end_indices),
            indices(self.opponent_team_ids),
            np.stack(self.static_inputs) if self.static_inputs else np.empty((0, static_input_dim), dtype=np.float32),
            np.array(self.outputs, dtype=np.float64),
            np.array(self.game_dates, dtype='datetime64[ns]')
        )

def _print_progress(count: int):
    if count % 25000 == 0:
        print(f"\r\033[KData Chunks Processed: {count}", end="", flush=True)

def _game_positions(histories: Mapping[int, GameHistory]) -> dict[tuple[int, int], SequenceRead]:
    return {
        (subject_id, int(game_id)): SequenceRead(sequence_index, position, int(history.opponent_team_ids[position]))
        for sequence_index, (subject_id, history) in enumerate(histories.items())
        for position, game_id in enumerate(history.game_ids)
    }

def build_split_samples(
    histories: Mapping[int, GameHistory],
    evaluation_split: EvaluationSplit,
    minimum_past_games: int,
    chunk_step_size: int = 1,
    *,
    sequence_columns: Sequence[str],
    static_columns: Sequence[str],
    training_start_date: datetime | None = None,
    read_opponent_history: bool = False,
    print_debug: bool = False
    ) -> tuple[GameSequences, list[SequenceInputSamples]]:
    """Builds every labeled sample from the histories, split into training, validation and test."""

    if training_start_date is not None:
        histories = {
            subject_id: history.starting_on(training_start_date)
            for subject_id, history in histories.items()
            if history.game_dates[-1] >= np.datetime64(training_start_date)
        }

    # Training rows come from played games, so none of their values should be missing.
    for history in histories.values():
        check_columns_are_finite(history.sequence_values, sequence_columns, "past game columns")
        check_columns_are_finite(history.static_values, static_columns, "predicted game columns")
        check_columns_are_finite(
            history.outputs.reshape(-1, 1), [OUTPUT], "values a model is fit against"
        )

    static_input_dim = next((len(history.static_input(0)) for history in histories.values()), 0)
    sequence_count = 2 if read_opponent_history else 1
    positions = _game_positions(histories) if read_opponent_history else {}

    sequences: list[np.ndarray] = []
    sequence_opponent_team_ids: list[np.ndarray] = []
    training_game_counts: list[int] = []
    all_samples = [_SampleAccumulator() for _ in SPLIT_NAMES]

    count: int = 0
    for sequence_index, (subject_id, history) in enumerate(histories.items()):
        sequences.append(history.sequence_values)
        sequence_opponent_team_ids.append(history.opponent_team_ids)

        splits = evaluation_split.splits_of(subject_id, history.game_ids, history.game_dates)

        # The scalers are only fit on the training games.
        training_game_counts.append(int((splits == TRAINING_SPLIT).sum()))

        for index in range(minimum_past_games, history.game_count, chunk_step_size):
            if print_debug:
                _print_progress(count)
                count += 1

            if not history.is_sample_row[index]:
                continue

            opponent_team_id = int(history.opponent_team_ids[index])
            reads = [SequenceRead(sequence_index, index, opponent_team_id)]

            if read_opponent_history:
                opponent = positions.get((opponent_team_id, int(history.game_ids[index])))

                if opponent is None or opponent.end_index < minimum_past_games:
                    continue

                reads.append(opponent)

            all_samples[splits[index]].add(
                reads,
                history.static_input(index),
                history.outputs[index],
                history.game_dates[index]
            )

    if print_debug:
        print("")

    game_sequences = GameSequences(
        sequences,
        sequence_opponent_team_ids,
        np.array(training_game_counts, dtype=np.int64)
    )

    return (
        game_sequences,
        [samples.to_samples(static_input_dim, sequence_count) for samples in all_samples]
    )

@dataclass(frozen=True)
class SequenceToRead():
    """A subject's past games and opponents, used as input for a prediction."""

    past_games: np.ndarray
    """Shape: (games, sequence features). Sorted oldest first."""

    past_opponent_team_ids: np.ndarray

    opponent_team_id: int
    """ID of the team the subject plays in the predicted game."""

def read_up_to(history: GameHistory, index: int) -> SequenceToRead:
    """Returns the subject's games before the given index, plus the opponent at that index."""

    return SequenceToRead(
        history.sequence_values[:index],
        history.opponent_team_ids[:index],
        int(history.opponent_team_ids[index])
    )

def build_inference_sample(
    sides: Sequence[SequenceToRead],
    static_input: np.ndarray
    ) -> tuple[GameSequences, SequenceInputSamples]:
    """Builds the single sample used for a prediction from each subject's past games and the static input."""

    samples = SequenceInputSamples(
        np.arange(len(sides), dtype=np.int64).reshape(1, -1),
        np.array([[len(side.past_games) for side in sides]], dtype=np.int64),
        np.array([[side.opponent_team_id for side in sides]], dtype=np.int64),
        static_input.reshape(1, -1),
        np.zeros(1, dtype=np.float64)
    )

    # Training game counts are 0 because these games aren't used for training.
    game_sequences = GameSequences(
        [side.past_games for side in sides],
        [side.past_opponent_team_ids for side in sides],
        np.zeros(len(sides), dtype=np.int64)
    )

    return (game_sequences, samples)
