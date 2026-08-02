import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from dataclasses import dataclass, replace
from torch.utils.data import Dataset
from typing import Any, cast
from sklearn.preprocessing import StandardScaler

def convert_labeled_data_to_numpy(
    data: list[dict[str, pd.DataFrame]] | list[pd.DataFrame] | list[pd.Series],
    flatten: bool
) -> np.ndarray:
    """
    Converts the given dataframes into a format that can be easily used for normalization and training.

    If flatten is set to True, each element in the resulting np.ndarray will correspond to a 1-dimensional structure of features.
    """

    def to_array(df: pd.DataFrame | pd.Series) -> np.ndarray:
        arr = df.to_numpy(dtype=np.float32)
        return arr.reshape(-1) if flatten else arr

    def process_dict(chunk: dict[str, pd.DataFrame]) -> np.ndarray:
        arrays = []
        for _, df in chunk.items():
            try:
                arrays.append(to_array(df))
            except Exception as e:
                print(f"Error processing dataframe: {e}\n{df}")
        return np.concatenate(arrays)

    if not data:
        return np.empty(0, dtype=np.float32)

    first = data[0]

    if isinstance(first, dict):
        samples = [process_dict(cast(dict[str, pd.DataFrame], chunk)) for chunk in data]
    elif isinstance(first, (pd.DataFrame, pd.Series)):
        samples = [to_array(cast(pd.DataFrame | pd.Series, chunk)) for chunk in data]
    else:
        raise ValueError(f"Unsupported chunk type: {type(first).__name__}. Expected dict, DataFrame, or Series.")
    
    return np.stack(samples)

def standardize(
    training_data: np.ndarray,
    validation_data: np.ndarray,
    test_data: np.ndarray    
    ) -> tuple[
        np.ndarray, 
        np.ndarray,
        np.ndarray,
        StandardScaler
    ]:
    """
    Fit StandardScalers on the training data and transform the test.
    """

    scaler = StandardScaler()

    train_norm = scaler.fit_transform(training_data)
    validation_norm = scaler.transform(validation_data)
    test_norm = scaler.transform(test_data)
    
    return (
        train_norm, validation_norm, test_norm, scaler
    )

def to_tensor(array: np.ndarray) -> torch.Tensor:
    return torch.tensor(array, dtype=torch.float32)

def process_labeled_data_for_training(
        input_training_data: list, 
        output_training_data: list, 
        input_validation_data: list, 
        output_validation_data: list, 
        input_test_data: list, 
        output_test_data: list,
        flatten: bool,
        standardize_input: bool = False,
        standardize_output: bool = False
    ) -> tuple[
        torch.Tensor, torch.Tensor,
        torch.Tensor, torch.Tensor,
        torch.Tensor, torch.Tensor,
        StandardScaler | None,
        StandardScaler | None
    ]:
    """
    Converts labeled data in the form of lists of (dataframes or dicts of dataframes) into data for machine learning. 
    The resulting data can be normalized and in the form of tensors.

    The returned data is in the form of a tuple consisting of:
    (
    input training dataset, output training dataset, 
    input validation data, output validation dataset, 
    input test dataset, output test dataset,
    input_scaler if scale_input is True, otherwise None,
    output_scaler if scale_output is True, otherwise None
    )
    """
    
    input_train_numpy = convert_labeled_data_to_numpy(input_training_data, flatten)
    output_train_numpy = convert_labeled_data_to_numpy(output_training_data, flatten)
    input_val_numpy = convert_labeled_data_to_numpy(input_validation_data, flatten)
    output_val_numpy = convert_labeled_data_to_numpy(output_validation_data, flatten)
    input_test_numpy = convert_labeled_data_to_numpy(input_test_data, flatten)
    output_test_numpy = convert_labeled_data_to_numpy(output_test_data, flatten)

    input_scaler = None
    output_scaler = None
    if standardize_input:
        input_train_numpy, input_val_numpy, input_test_numpy, input_scaler = standardize(
            input_train_numpy, input_val_numpy, input_test_numpy
            )
    if standardize_output:
        output_train_numpy, output_val_numpy, output_test_numpy, output_scaler = standardize(
            output_train_numpy, output_val_numpy, output_test_numpy
            )

    input_train_tensor = to_tensor(input_train_numpy)
    output_train_tensor = to_tensor(output_train_numpy)
    input_val_tensor = to_tensor(input_val_numpy)
    output_val_tensor = to_tensor(output_val_numpy)
    input_test_tensor = to_tensor(input_test_numpy)
    output_test_tensor = to_tensor(output_test_numpy)

    return (
        input_train_tensor, output_train_tensor, 
        input_val_tensor, output_val_tensor, 
        input_test_tensor, output_test_tensor,
        input_scaler, output_scaler
        )

def _adjust_classification_output_tensor(
    outputs: torch.Tensor,
    min_output_value: int,
    num_classifications: int | None
    ) -> torch.Tensor:
    """
    Shifts the outputs so the lowest one becomes class 0, then folds anything past the last class
    into it. Values below the minimum are folded into class 0, because a negative class index
    would silently corrupt Cross Entropy Loss.
    """

    adjusted = outputs.squeeze(-1).long().sub(min_output_value)
    maximum = None if num_classifications is None else num_classifications - 1

    return adjusted.clamp(min=0, max=maximum)

def _adjust_classification_outputs(
    outputs: np.ndarray,
    min_output_value: int,
    num_classifications: int | None
    ) -> np.ndarray:
    """
    The array form of _adjust_classification_output_tensor, so both paths label data the same way.
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

def process_labeled_data_for_classification_training(
        input_training_data: list,
        output_training_data: list, 
        input_validation_data: list, 
        output_validation_data: list, 
        input_test_data: list, 
        output_test_data: list,
        flatten: bool,
        min_output_value: int = 0,
        num_classifications: int | None = None,
        standardize_input: bool = False,
    ) -> tuple[
        torch.Tensor, torch.Tensor,
        torch.Tensor, torch.Tensor,
        torch.Tensor, torch.Tensor,
        StandardScaler | None
    ]:
    """
    Converts labeled data in the form of lists of (dataframes or dicts of dataframes) into data for classification with Cross Entropy Loss. 
    The resulting data is in the form of tensors.
    The input data can be normalized.
    The output data will be formed into 1 dimensional long numpy arrays.
    The output data will be subtracted by min_output_value so that the outputs start from 0.
    The output data will be clamped by num_classifications so that there are that many total values in the dataset.
    The output data will be squeezed to be a one dimensional tensor.

    The returned data is in the form of a tuple consisting of:
    (
    input training dataset, output training dataset, 
    input validation data, output validation dataset, 
    input test dataset, output test dataset,
    input_scaler if scale_input is True, otherwise None
    )
    """

    (input_train, output_train,
     input_val, output_val,
     input_test, output_test,
     input_scaler_or_none, ALWAYS_NONE
     ) = process_labeled_data_for_training(
         input_training_data,
         output_training_data,
         input_validation_data,
         output_validation_data,
         input_test_data,
         output_test_data,
         flatten,
         standardize_input,
         False
         )

    output_train, output_val, output_test = (
        _adjust_classification_output_tensor(output, min_output_value, num_classifications)
        for output in (output_train, output_val, output_test)
    )

    return (
        input_train, 
        output_train,
        input_val,
        output_val, 
        input_test,
        output_test, 
        input_scaler_or_none
        )

def process_labeled_input(
    input,
    flatten: bool
    ) -> np.ndarray:

    input_numpy = convert_labeled_data_to_numpy([input], flatten)

    return input_numpy

# Sequence data
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

        return self._outputs

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

def process_sequence_labeled_data_for_classification_training(
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
    Converts sequence labeled data into datasets for classification with Cross Entropy Loss.
    The outputs are shifted by min_output_value and clamped by num_classifications, matching
    process_labeled_data_for_classification_training.

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

def process_sequence_labeled_input(
    player_game_sequences: PlayerGameSequences,
    samples: SequenceInputSamples,
    max_sequence_length: int | None,
    sequence_scaler: StandardScaler,
    static_scaler: StandardScaler
    ) -> SequenceGameDataset:
    """
    Applies already fit scalers to sequence labeled data so that it can be inferenced on.
    """

    player_game_sequences, (samples,) = _standardize_sequence_data(
        player_game_sequences,
        [samples],
        sequence_scaler,
        static_scaler
    )

    return SequenceGameDataset(player_game_sequences, samples, max_sequence_length)