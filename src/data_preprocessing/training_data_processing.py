import pandas as pd
import numpy as np
import torch
from typing import cast
from sklearn.preprocessing import StandardScaler

# TODO: Refactor processing for unflattened data with sequence and static data

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

def process_raw_data_for_training(
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
    Converts raw data in the form of lists of (dataframes or dicts of dataframes) into data for machine learning. 
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

def process_raw_data_for_classification_training(
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
    Converts raw data in the form of lists of (dataframes or dicts of dataframes) into data for classification with Cross Entropy Loss. 
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
     ) = process_raw_data_for_training(
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
    
    output_train = output_train.squeeze(-1).long()
    output_val = output_val.squeeze(-1).long()
    output_test = output_test.squeeze(-1).long()

    output_train = output_train.sub(min_output_value)
    output_val = output_val.sub(min_output_value)
    output_test = output_test.sub(min_output_value)

    if num_classifications is not None:
        output_train = output_train.clamp(max=num_classifications - 1)
        output_val = output_val.clamp(max=num_classifications - 1)
        output_test = output_test.clamp(max=num_classifications - 1)
    
    return (
        input_train, 
        output_train,
        input_val,
        output_val, 
        input_test,
        output_test, 
        input_scaler_or_none
        )