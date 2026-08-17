from typing import Any, cast
from dataclasses import dataclass, replace

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset
from sklearn.preprocessing import StandardScaler

def _adjust_classification_outputs(
    outputs: np.ndarray,
    min_output_value: int,
    num_classifications: int | None,
    output_value_step: int = 1,
    impossible_value: int | None = None
    ) -> np.ndarray:
    """
    Turns the values into the classes a model is fit against, folding anything outside the class
    range into the nearest end of it.

    Args:
        output_value_step is how many values one class covers. At one every value is its own class.
        Above one the classes are buckets, which is what a model with too few samples to fill a class
        per value is given.

        impossible_value is a whole number the statistic cannot take, such as a point differential of
        zero. It is not on the line at all, so everything above it counts one step lower and every
        class still covers output_value_step outcomes.
    """

    values = outputs.astype(np.int64)
    steps = values - min_output_value

    if impossible_value is not None:
        steps = steps - (values > impossible_value)

    maximum = None if num_classifications is None else num_classifications - 1

    return (steps // output_value_step).clip(min=0, max=maximum)

def summarize_classification_outputs(
    outputs: torch.Tensor,
    num_classifications: int,
    output_value_step: int = 1
    ) -> dict[str, Any]:
    """
    Describes the labels a classification model will be trained on.

    Both ends fold: anything below the range counts as the first class and anything above it as the
    last. For a stat with an order, a large share in either end class means the range is too narrow
    to describe that tail, so both are reported.
    """

    total = len(outputs)
    summary = {"samples": total, "classes": num_classifications, "values per class": output_value_step}

    if total == 0:
        return summary

    in_first_class = int((outputs == 0).sum())
    in_last_class = int((outputs == num_classifications - 1).sum())

    return {
        **summary,
        "lowest class": int(outputs.min()),
        "highest class": int(outputs.max()),
        "mean class": float(outputs.float().mean()),
        "in the first class": f"{in_first_class:,} ({in_first_class / total:.2%})",
        "in the last class": f"{in_last_class:,} ({in_last_class / total:.2%})"
    }

@dataclass
class GameSequences():
    """
    Every game played by each subject, stored once so that the samples reading them only need to
    hold an index instead of their own copy of the games.

    A subject is whoever the model predicts about, a player or a team. Each subject's games must be
    ordered from oldest to newest.
    """

    sequences: list[np.ndarray]
    """Per subject, the sequence features of every game played, shaped (games, sequence features)."""

    opponent_team_ids: list[np.ndarray]
    """Per subject, the team id faced in every game played."""

    training_game_counts: np.ndarray
    """Per subject, how many of the oldest games belong to the training split."""

@dataclass
class SequenceInputSamples():
    """
    One entry per prediction, holding the static data of the predicted game and a reference into
    the games that came before it.

    A sample may read more than one subject's games, which is what a model about a whole game does:
    it reads both teams rather than being asked about one of them. Every array naming a subject is
    therefore shaped (samples, sequences), with the sequences of one sample always in the same order.
    """

    sequence_indices: np.ndarray
    """Per sample and sequence, which subject of a GameSequences it reads."""

    sequence_end_indices: np.ndarray
    """Per sample and sequence, the exclusive end of the games that came before the predicted game."""

    opponent_team_ids: np.ndarray
    """Per sample and sequence, the team id that subject faces in the predicted game."""

    static_inputs: np.ndarray
    """Shaped (samples, static features)."""

    outputs: np.ndarray
    """What the model is fit against, which a classification build rewrites as the class that happened."""

    game_dates: np.ndarray | None = None
    """
    When each predicted game was played, shaped (samples,).

    Carried so a finished split can say which stretch of calendar it covers, and so a naive floor
    can be worked out from the training games nearest the ones being scored. A prediction carries
    none, because there is nothing to report about a single sample.
    """

    values: np.ndarray | None = None
    """
    What actually happened, kept as it was recorded.

    A classification build folds the ends of its range and buckets what is left, so a class is not
    the value. Scoring a finished model reads this instead, and a model whose classes are buckets is
    then measured in the units a reader knows rather than in classes of its own width.
    """

    @property
    def sequence_count(self) -> int:
        return self.sequence_indices.shape[1]

class SequenceGameDataset(Dataset):
    """
    Yields (past games per sequence, static input, output) per sample.

    Every game in a sequence carries an extra flag that is 1 when that game was played against the
    opponent faced in the predicted game, so a sequence model can tell those games apart.
    """

    def __init__(
        self,
        game_sequences: GameSequences,
        samples: SequenceInputSamples,
        max_sequence_length: int | None
        ):
        """
        Args:
            max_sequence_length: how many of the most recent games to read, or None for all of them.

        The games are held by reference, so every dataset built from the same GameSequences shares
        one copy of them.
        """

        self.game_sequences = game_sequences
        self.samples = samples
        self.max_sequence_length = max_sequence_length
        self._outputs: torch.Tensor | None = None

    def __len__(self) -> int:
        return len(self.samples.sequence_indices)

    def _past_games(self, index: int, sequence: int) -> torch.Tensor:
        sequence_index = int(self.samples.sequence_indices[index, sequence])
        end_index = int(self.samples.sequence_end_indices[index, sequence])
        start_index = 0 if self.max_sequence_length is None else max(0, end_index - self.max_sequence_length)

        past_games = self.game_sequences.sequences[sequence_index][start_index : end_index]
        played_against_predicted_opponent = (
            self.game_sequences.opponent_team_ids[sequence_index][start_index : end_index]
            == self.samples.opponent_team_ids[index, sequence]
        ).astype(np.float32).reshape(-1, 1)

        return torch.from_numpy(
            np.concatenate((past_games, played_against_predicted_opponent), axis=1)
        )

    def __getitem__(self, index: int) -> tuple[list[torch.Tensor], torch.Tensor, torch.Tensor]:
        return (
            [self._past_games(index, sequence) for sequence in range(self.sequence_count)],
            torch.from_numpy(self.samples.static_inputs[index]),
            self.outputs[index]
        )

    @property
    def outputs(self) -> torch.Tensor:
        # Built once instead of per sample read. getattr keeps datasets cached before this
        # existed loadable, since a pickled dataset never runs __init__.
        if getattr(self, "_outputs", None) is None:
            self._outputs = torch.from_numpy(self.samples.outputs)

        return cast(torch.Tensor, self._outputs)

    @property
    def sequence_count(self) -> int:
        return self.samples.sequence_count

    @property
    def sequence_input_dim(self) -> int:
        return self.game_sequences.sequences[0].shape[1] + 1

    @property
    def static_input_dim(self) -> int:
        return self.samples.static_inputs.shape[1]

def collate_sequence_batch(
    batch: list[tuple[list[torch.Tensor], torch.Tensor, torch.Tensor]]
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Pads every sequence of a batch to the longest one in it.

    A sample's sequences are laid out next to each other and in the order the sample lists them, so
    a batch of samples reading two sequences is twice as many rows as it has samples. That is what
    lets one GRU read all of them in one pass and the model fold them back into one row per sample.

    Returns (padded sequences, unpadded sequence lengths, static inputs, outputs).
    """

    sample_sequences, static_inputs, outputs = zip(*batch)
    sequences = [sequence for sample in sample_sequences for sequence in sample]

    return (
        nn.utils.rnn.pad_sequence(sequences, batch_first=True),
        torch.tensor([len(sequence) for sequence in sequences]),
        torch.stack(static_inputs),
        torch.stack(outputs)
    )

def _standardize_sequence_data(
    game_sequences: GameSequences,
    all_samples: list[SequenceInputSamples],
    sequence_scaler: StandardScaler,
    static_scaler: StandardScaler
    ) -> tuple[GameSequences, list[SequenceInputSamples]]:

    standardized_sequences = replace(
        game_sequences,
        sequences=[
            sequence_scaler.transform(sequence).astype(np.float32)
            for sequence in game_sequences.sequences
        ]
    )
    standardized_samples = [
        replace(samples, static_inputs=static_scaler.transform(samples.static_inputs).astype(np.float32))
        for samples in all_samples
    ]

    return standardized_sequences, standardized_samples

def build_classification_datasets(
    game_sequences: GameSequences,
    training_samples: SequenceInputSamples,
    validation_samples: SequenceInputSamples,
    test_samples: SequenceInputSamples,
    max_sequence_length: int | None,
    min_output_value: int = 0,
    num_classifications: int | None = None,
    output_value_step: int = 1,
    impossible_value: int | None = None,
    standardize_input: bool = False
    ) -> tuple[
        SequenceGameDataset,
        SequenceGameDataset,
        SequenceGameDataset,
        StandardScaler | None,
        StandardScaler | None
    ]:
    """
    Builds the three splits as classification datasets, with the outputs turned into the classes the
    model is fit against and what actually happened kept beside them.

    Args:
        min_output_value is the value the first class stands for, and output_value_step how many
        values one class covers. Anything outside the range folds into the nearest end, and
        impossible_value names a whole number inside it that the statistic cannot take.

    The scalers are fit only on the games and samples of the training split, and come back None
    unless standardize_input is set.
    """

    all_samples = [training_samples, validation_samples, test_samples]

    sequence_scaler = None
    static_scaler = None
    if standardize_input:
        training_games = np.concatenate([
            sequence[:training_game_count]
            for sequence, training_game_count
            in zip(game_sequences.sequences, game_sequences.training_game_counts)
        ])

        sequence_scaler = StandardScaler().fit(training_games)
        static_scaler = StandardScaler().fit(training_samples.static_inputs)

        game_sequences, all_samples = _standardize_sequence_data(
            game_sequences,
            all_samples,
            sequence_scaler,
            static_scaler
        )

    all_samples = [
        replace(
            samples,
            outputs=_adjust_classification_outputs(
                samples.outputs,
                min_output_value,
                num_classifications,
                output_value_step,
                impossible_value
            ),
            values=samples.outputs
        )
        for samples in all_samples
    ]

    training_dataset, validation_dataset, test_dataset = (
        SequenceGameDataset(game_sequences, samples, max_sequence_length)
        for samples in all_samples
    )

    return (
        training_dataset,
        validation_dataset,
        test_dataset,
        sequence_scaler,
        static_scaler
    )

def build_inference_dataset(
    game_sequences: GameSequences,
    samples: SequenceInputSamples,
    max_sequence_length: int | None,
    sequence_scaler: StandardScaler,
    static_scaler: StandardScaler
    ) -> SequenceGameDataset:
    """Applies a saved model's own scalers, so it reads a new sample the way it was trained."""

    game_sequences, (samples,) = _standardize_sequence_data(
        game_sequences,
        [samples],
        sequence_scaler,
        static_scaler
    )

    return SequenceGameDataset(game_sequences, samples, max_sequence_length)
