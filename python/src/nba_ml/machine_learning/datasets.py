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
    """Converts values to class indices. Values outside the range are clipped to the first or last class."""

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
    """Returns summary stats of the class labels a model will be trained on."""

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
    """Every subject's games, stored once and sorted oldest to newest."""

    sequences: list[np.ndarray]
    """One array per subject with the sequence features of every game. Shape: (games, sequence features)."""

    opponent_team_ids: list[np.ndarray]
    """One array per subject with the opponent team ID of every game."""

    training_game_counts: np.ndarray
    """For each subject, the number of games (counted from the oldest) in the training split."""

@dataclass
class SequenceInputSamples():
    """One entry per sample: its static input and indices pointing to its past games."""

    sequence_indices: np.ndarray
    """For each sample and sequence, the index of the subject in GameSequences."""

    sequence_end_indices: np.ndarray
    """For each sample and sequence, the end index (exclusive) of the games before the predicted game."""

    opponent_team_ids: np.ndarray
    """For each sample and sequence, the ID of the team the subject plays in the predicted game."""

    static_inputs: np.ndarray
    """Shape: (samples, static features)."""

    outputs: np.ndarray
    """Target values the model is trained on."""

    game_dates: np.ndarray | None = None
    """Date of each predicted game. Shape: (samples,)."""

    values: np.ndarray | None = None
    """The actual values before they were converted to classes."""

    @property
    def sequence_count(self) -> int:
        return self.sequence_indices.shape[1]

class SequenceGameDataset(Dataset):
    """Each item is (past games for each sequence, static input, output)."""

    def __init__(
        self,
        game_sequences: GameSequences,
        samples: SequenceInputSamples,
        max_sequence_length: int | None
        ):
        """max_sequence_length is the number of most recent games to use, or None for all of them."""

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
        # getattr is used so datasets pickled before this attribute existed still load.
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
    """Pads a batch to its longest sequence. Returns (sequences, lengths, static inputs, outputs)."""

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
    standardize_input: bool = False,
    input_scalers: tuple[StandardScaler, StandardScaler] | None = None
    ) -> tuple[
        SequenceGameDataset,
        SequenceGameDataset,
        SequenceGameDataset,
        StandardScaler | None,
        StandardScaler | None
    ]:
    """Builds the training, validation and test datasets. Scalers are fit on training data only."""

    all_samples = [training_samples, validation_samples, test_samples]

    sequence_scaler = None
    static_scaler = None
    if input_scalers is not None and not standardize_input:
        raise ValueError("Input scalers can only be applied while standardizing inputs.")

    if standardize_input:
        if input_scalers is None:
            training_games = np.concatenate([
                sequence[:training_game_count]
                for sequence, training_game_count
                in zip(game_sequences.sequences, game_sequences.training_game_counts)
            ])

            sequence_scaler = StandardScaler().fit(training_games)
            static_scaler = StandardScaler().fit(training_samples.static_inputs)
        else:
            sequence_scaler, static_scaler = input_scalers

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
    """Builds a dataset for inference, standardized with the scalers saved with the model."""

    game_sequences, (samples,) = _standardize_sequence_data(
        game_sequences,
        [samples],
        sequence_scaler,
        static_scaler
    )

    return SequenceGameDataset(game_sequences, samples, max_sequence_length)
