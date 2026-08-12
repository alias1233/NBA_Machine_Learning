"""
Turning a finished feature frame into the samples a model is fit on.

Every model here predicts one thing from the games played before it. Only the columns differ between
families, so the cutting, the splitting and the sample loop sit here and a family says nothing but
which columns it wants and what a sample is.

A sample is read off one row and reads the games of whoever that row is about. A family predicting a
whole game rather than one side of it says so twice: only one of a game's two rows may be read off,
and the sample reads the opposing team's games as well as its own.

The frame this reads must already hold one row per subject per game, sorted by subject and then by
date, with every column already engineered.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from nba_ml.machine_learning.datasets import GameSequences, SequenceInputSamples

OUTPUT = "OUTPUT"
"""The column holding the value a model is fit against, whatever the family reads it off."""

TRAINING_SPLIT = 0
VALIDATION_SPLIT = 1
TEST_SPLIT = 2

@dataclass(frozen=True)
class GameHistory():
    """
    One subject's games, already reduced to the numbers a model reads, oldest game first.

    Everything is a plain array rather than a dataframe, so building a sample is a slice instead of
    hundreds of thousands of small pandas objects.
    """

    static_subject_values: np.ndarray
    """The subject's own unchanging information, shaped (subject features,). Empty when it has none."""

    game_ids: np.ndarray
    game_dates: np.ndarray
    sequence_values: np.ndarray
    """Shaped (games, sequence features)."""

    static_values: np.ndarray
    """Shaped (games, static features)."""

    opponent_team_ids: np.ndarray
    outputs: np.ndarray

    is_sample_row: np.ndarray
    """
    Per game, whether a sample may be read off it.

    Every row qualifies unless the family said otherwise. A game statistic belongs to the game rather
    than to either side, so its family reads one row of the two and the game becomes one sample.
    """

    @property
    def game_count(self) -> int:
        return len(self.game_dates)

    def static_input(self, index: int) -> np.ndarray:
        """The static half of one sample's input, read off the game being predicted."""

        return np.concatenate((self.static_subject_values, self.static_values[index]))

NO_STATIC_SUBJECT_VALUES = np.empty(0, dtype=np.float32)
"""What a subject the model knows nothing unchanging about carries, such as a team."""

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
    """
    Cuts a finished feature frame into one history per subject.

    The columns are pulled out as whole arrays once and then sliced, which is why every subject's
    games have to sit together in the frame.

    Args:
        static_subject_values holds what never changes about a subject, keyed by its id. Leave it
        unset for a subject that carries none.
        sample_row_column names a column that is true for the rows a sample may be read off. Leave
        it unset where every row may be.
    """

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
    """One history a sample reads, and where in it the sample stops reading."""

    sequence_index: int
    """Which subject of a GameSequences this is."""

    end_index: int
    """The exclusive end of the games that came before the predicted one."""

    opponent_team_id: int
    """Who this subject faces in the predicted game, which marks those games inside the sequence."""

class _SampleAccumulator():
    """Collects the samples of one split before they are packed into arrays."""

    def __init__(self):
        self.sequence_indices: list[list[int]] = []
        self.sequence_end_indices: list[list[int]] = []
        self.opponent_team_ids: list[list[int]] = []
        self.static_inputs: list[np.ndarray] = []
        self.outputs: list[float] = []

    def add(
        self,
        reads: Sequence[SequenceRead],
        static_input: np.ndarray,
        output: float
        ):
        self.sequence_indices.append([read.sequence_index for read in reads])
        self.sequence_end_indices.append([read.end_index for read in reads])
        self.opponent_team_ids.append([read.opponent_team_id for read in reads])
        self.static_inputs.append(static_input)
        self.outputs.append(output)

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
            np.array(self.outputs, dtype=np.float64)
        )

def _print_progress(count: int):
    if count % 25000 == 0:
        print(f"\r\033[KData Chunks Processed: {count}", end="", flush=True)

def _game_positions(histories: Mapping[int, GameHistory]) -> dict[tuple[int, int], SequenceRead]:
    """
    Where every subject's every game sits, keyed by that subject and the game.

    This is what lets a sample read a second subject of the same game. Only a family whose subjects
    are teams asks for one, because only then does the other side of a game have a history to read.
    """

    return {
        (subject_id, int(game_id)): SequenceRead(sequence_index, position, int(history.opponent_team_ids[position]))
        for sequence_index, (subject_id, history) in enumerate(histories.items())
        for position, game_id in enumerate(history.game_ids)
    }

def build_split_samples(
    histories: Mapping[int, GameHistory],
    split_start_dates: Iterable[datetime],
    minimum_past_games: int,
    chunk_step_size: int = 1,
    *,
    read_opponent_history: bool = False,
    print_debug: bool = False
    ) -> tuple[GameSequences, list[SequenceInputSamples]]:
    """
    Builds every labeled sample the histories hold, split by date.

    Each subject's games are kept once and the samples only hold where in them to read, so that a
    sample can look back over a long history without storing its own copy of it.

    Games played against the predicted game's opponent are marked inside the sequence itself, so a
    sample is kept even when the subject has rarely faced them.

    Args:
        split_start_dates are the boundaries between splits, oldest first. A game on a boundary
        stays in the earlier split, so a model is only ever scored on games played after the ones it
        learned from.
        minimum_past_games is how many games must sit behind one before it can be a sample. Every
        history a sample reads has to clear it.
        read_opponent_history adds the opposing team's own games as a second sequence. Only a family
        whose subjects are teams can ask for this.

    Returns:
        (the games of every subject, one set of samples per split, oldest split first)
    """

    boundaries = np.array(list(split_start_dates), dtype='datetime64[ns]')
    static_input_dim = next((len(history.static_input(0)) for history in histories.values()), 0)
    sequence_count = 2 if read_opponent_history else 1
    positions = _game_positions(histories) if read_opponent_history else {}

    sequences: list[np.ndarray] = []
    sequence_opponent_team_ids: list[np.ndarray] = []
    training_game_counts: list[int] = []
    all_samples = [_SampleAccumulator() for _ in range(len(boundaries) + 1)]

    count: int = 0
    for sequence_index, history in enumerate(histories.values()):
        sequences.append(history.sequence_values)
        sequence_opponent_team_ids.append(history.opponent_team_ids)

        splits = np.searchsorted(boundaries, history.game_dates, side='left')

        # Only the oldest games are visible to the training split, so the scalers can be fit without
        # seeing validation or test games.
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
                # The other side of the same game, read up to it exactly as this one is. A side with
                # too little behind it is no sample, because a sequence cannot be empty.
                opponent = positions.get((opponent_team_id, int(history.game_ids[index])))

                if opponent is None or opponent.end_index < minimum_past_games:
                    continue

                reads.append(opponent)

            all_samples[splits[index]].add(
                reads,
                history.static_input(index),
                history.outputs[index]
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
    """
    One subject a prediction reads: the games behind the predicted one, and who they face in it.

    The games are given outright rather than as a position in a history, because the two halves of a
    prediction come from different places. The games behind it come from a build the whole league
    shares, and the game being predicted is assembled per request.
    """

    past_games: np.ndarray
    """Shaped (games, sequence features), oldest first."""

    past_opponent_team_ids: np.ndarray
    """Who the subject faced in each of those games, which is what marks the ones against this one."""

    opponent_team_id: int
    """Who the subject faces in the game being predicted."""

def read_up_to(history: GameHistory, index: int) -> SequenceToRead:
    """One subject's side of a prediction, taken out of a history that holds the predicted game."""

    return SequenceToRead(
        history.sequence_values[:index],
        history.opponent_team_ids[:index],
        int(history.opponent_team_ids[index])
    )

def build_inference_sample(
    sides: Sequence[SequenceToRead],
    static_input: np.ndarray
    ) -> tuple[GameSequences, SequenceInputSamples]:
    """
    The one sample a prediction runs: the games each side reads, and the game being predicted.

    Args:
        sides are the subjects the model reads, in the order it reads them.
        static_input is everything read off the game being predicted, which belongs to the side the
        answer is read off.
    """

    samples = SequenceInputSamples(
        np.arange(len(sides), dtype=np.int64).reshape(1, -1),
        np.array([[len(side.past_games) for side in sides]], dtype=np.int64),
        np.array([[side.opponent_team_id for side in sides]], dtype=np.int64),
        static_input.reshape(1, -1),
        np.zeros(1, dtype=np.float64)
    )

    # None of these games belong to a training split, since nothing is being fit.
    game_sequences = GameSequences(
        [side.past_games for side in sides],
        [side.past_opponent_team_ids for side in sides],
        np.zeros(len(sides), dtype=np.int64)
    )

    return (game_sequences, samples)
