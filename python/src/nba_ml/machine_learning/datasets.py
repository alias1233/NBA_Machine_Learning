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
    num_classifications: int | None
    ) -> np.ndarray:
    """
    Shifts the outputs so the lowest one becomes class 0, then folds anything past the last class
    into it. Values below the minimum are folded into class 0, because a negative class index
    would silently corrupt Cross Entropy Loss.
    """

    adjusted = outputs.astype(np.int64) - min_output_value
    maximum = None if num_classifications is None else num_classifications - 1

    return adjusted.clip(min=0, max=maximum)

def summarize_classification_outputs(
    outputs: torch.Tensor,
    num_classifications: int
    ) -> dict[str, Any]:
    """
    Describes the labels a classification model will be trained on. Anything above the last class
    was folded into it, so a large share in the last class means the class count is too low to
    describe the tail of the stat.
    """

    total = len(outputs)
    if total == 0:
        return {"samples": 0, "classes": num_classifications}

    in_last_class = int((outputs == num_classifications - 1).sum())

    return {
        "samples": total,
        "classes": num_classifications,
        "lowest class": int(outputs.min()),
        "highest class": int(outputs.max()),
        "mean class": float(outputs.float().mean()),
        "in the last class": f"{in_last_class:,} ({in_last_class / total:.2%})"
    }

@dataclass
class PlayerGameSequences():
    """
    Every game played by each player, stored once so that the samples reading them only need to
    hold an index instead of their own copy of the games.

    Each player's games must be ordered from oldest to newest.
    """

    sequences: list[np.ndarray]
    """Per player, the sequence features of every game played, shaped (games, sequence features)."""

    opponent_team_ids: list[np.ndarray]
    """Per player, the team id faced in every game played."""

    training_game_counts: np.ndarray
    """Per player, how many of the oldest games belong to the training split."""

@dataclass
class SequenceInputSamples():
    """
    One entry per prediction, holding the static data of the predicted game and a reference into
    the games that came before it.
    """

    player_indices: np.ndarray
    """Per sample, which player of a PlayerGameSequences the sample reads."""

    sequence_end_indices: np.ndarray
    """Per sample, the exclusive end of the games that came before the predicted game."""

    opponent_team_ids: np.ndarray
    """Per sample, the team id faced in the predicted game."""

    static_inputs: np.ndarray
    """Shaped (samples, static features)."""

    outputs: np.ndarray

class SequenceGameDataset(Dataset):
    """
    Yields (sequence of past games, static input, output) per sample.

    Every game in the sequence carries an extra flag that is 1 when that game was played against
    the predicted game's opponent, so a sequence model can tell those games apart.
    """

    def __init__(
        self,
        player_game_sequences: PlayerGameSequences,
        samples: SequenceInputSamples,
        max_sequence_length: int | None
        ):
        """
        Args:
            max_sequence_length: how many of the most recent games to read, or None for all of them.

        The games are held by reference, so every dataset built from the same PlayerGameSequences
        shares one copy of them.
        """

        self.player_game_sequences = player_game_sequences
        self.samples = samples
        self.max_sequence_length = max_sequence_length
        self._outputs: torch.Tensor | None = None

    def __len__(self) -> int:
        return len(self.samples.player_indices)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        player_index = int(self.samples.player_indices[index])
        end_index = int(self.samples.sequence_end_indices[index])
        start_index = 0 if self.max_sequence_length is None else max(0, end_index - self.max_sequence_length)

        past_games = self.player_game_sequences.sequences[player_index][start_index : end_index]
        played_against_predicted_opponent = (
            self.player_game_sequences.opponent_team_ids[player_index][start_index : end_index]
            == self.samples.opponent_team_ids[index]
        ).astype(np.float32).reshape(-1, 1)

        return (
            torch.from_numpy(np.concatenate((past_games, played_against_predicted_opponent), axis=1)),
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
    def sequence_input_dim(self) -> int:
        return self.player_game_sequences.sequences[0].shape[1] + 1

    @property
    def static_input_dim(self) -> int:
        return self.samples.static_inputs.shape[1]

def collate_sequence_batch(
    batch: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor]]
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Pads the sequences of a batch to its longest sequence.

    Returns (padded sequences, unpadded sequence lengths, static inputs, outputs).
    """

    sequences, static_inputs, outputs = zip(*batch)

    return (
        nn.utils.rnn.pad_sequence(list(sequences), batch_first=True),
        torch.tensor([len(sequence) for sequence in sequences]),
        torch.stack(static_inputs),
        torch.stack(outputs)
    )

def _standardize_sequence_data(
    player_game_sequences: PlayerGameSequences,
    all_samples: list[SequenceInputSamples],
    sequence_scaler: StandardScaler,
    static_scaler: StandardScaler
    ) -> tuple[PlayerGameSequences, list[SequenceInputSamples]]:

    standardized_sequences = replace(
        player_game_sequences,
        sequences=[
            sequence_scaler.transform(sequence).astype(np.float32)
            for sequence in player_game_sequences.sequences
        ]
    )
    standardized_samples = [
        replace(samples, static_inputs=static_scaler.transform(samples.static_inputs).astype(np.float32))
        for samples in all_samples
    ]

    return standardized_sequences, standardized_samples

def build_classification_datasets(
    player_game_sequences: PlayerGameSequences,
    training_samples: SequenceInputSamples,
    validation_samples: SequenceInputSamples,
    test_samples: SequenceInputSamples,
    max_sequence_length: int | None,
    min_output_value: int = 0,
    num_classifications: int | None = None,
    standardize_input: bool = False
    ) -> tuple[
        SequenceGameDataset,
        SequenceGameDataset,
        SequenceGameDataset,
        StandardScaler | None,
        StandardScaler | None
    ]:
    """
    Converts labeled data into datasets for classification with Cross Entropy Loss.
    The outputs are shifted by min_output_value and clamped by num_classifications.

    The scalers are fit only on games and samples belonging to the training split.

    The returned data is in the form of a tuple consisting of:
    (
    training dataset, validation dataset, test dataset,
    sequence_scaler and static_scaler if standardize_input is True, otherwise None
    )
    """

    all_samples = [training_samples, validation_samples, test_samples]

    sequence_scaler = None
    static_scaler = None
    if standardize_input:
        training_games = np.concatenate([
            sequence[:training_game_count]
            for sequence, training_game_count
            in zip(player_game_sequences.sequences, player_game_sequences.training_game_counts)
        ])

        sequence_scaler = StandardScaler().fit(training_games)
        static_scaler = StandardScaler().fit(training_samples.static_inputs)

        player_game_sequences, all_samples = _standardize_sequence_data(
            player_game_sequences,
            all_samples,
            sequence_scaler,
            static_scaler
        )

    all_samples = [
        replace(samples, outputs=_adjust_classification_outputs(samples.outputs, min_output_value, num_classifications))
        for samples in all_samples
    ]

    training_dataset, validation_dataset, test_dataset = (
        SequenceGameDataset(player_game_sequences, samples, max_sequence_length)
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
    player_game_sequences: PlayerGameSequences,
    samples: SequenceInputSamples,
    max_sequence_length: int | None,
    sequence_scaler: StandardScaler,
    static_scaler: StandardScaler
    ) -> SequenceGameDataset:
    """
    Applies already fit scalers to labeled data so that it can be inferenced on.
    """

    player_game_sequences, (samples,) = _standardize_sequence_data(
        player_game_sequences,
        [samples],
        sequence_scaler,
        static_scaler
    )

    return SequenceGameDataset(player_game_sequences, samples, max_sequence_length)