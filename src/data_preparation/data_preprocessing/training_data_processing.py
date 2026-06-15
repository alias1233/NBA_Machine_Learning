import pandas as pd
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler

def convert_dataframe_to_numpy(data: list[dict[str, pd.DataFrame]] | list[pd.DataFrame] | list[pd.Series], flatten: bool) -> np.ndarray:
    """
    Converts the given dataframes into a format that can be easily used for normalization and training.

    If flatten is set to True, each element in the resulting np.ndarray should correspond to 1 dimensional structure of features. 
    """

    # TODO: Potentially move the type checking outside of the loop so that it runs once per call instead of once per data chunk.
    
    samples = []

    if flatten:
        for chunk in data:
            if isinstance(chunk, dict):
                chunk_data = []
                for _, dataframe in chunk.items():
                    try:
                        chunk_data.append(dataframe.to_numpy(dtype=np.float32).reshape(-1))
                    except Exception as e:
                        print(e)
                        print(dataframe)

                samples.append(np.concatenate(chunk_data))

            elif isinstance(chunk, pd.DataFrame) or isinstance(chunk, pd.Series):
                samples.append(chunk.to_numpy(dtype=np.float32).reshape(-1))

            else:
                raise ValueError('Inputted data is not in the specified form.')
            
    else:
        for chunk in data:
            if isinstance(chunk, dict):
                chunk_data = []
                for _, dataframe in chunk.items():
                    try:
                        chunk_data.append(dataframe.to_numpy(dtype=np.float32))
                    except Exception as e:
                        print(e)
                        print(dataframe)

                samples.append(np.concatenate(chunk_data))

            elif isinstance(chunk, pd.DataFrame) or isinstance(chunk, pd.Series):
                samples.append(chunk.to_numpy(dtype=np.float32))

            else:
                raise ValueError('Inputted data is not in the specified form.')

    return np.stack(samples)


def normalize(
    input_train: np.ndarray,
    output_train: np.ndarray,
    input_val: np.ndarray,
    output_val: np.ndarray,
    input_test: np.ndarray,
    output_test: np.ndarray,
) -> tuple[
    np.ndarray, np.ndarray,
    np.ndarray, np.ndarray,
    np.ndarray, np.ndarray,
    StandardScaler, StandardScaler,
]:
    """
    Fit StandardScalers on the training split and transform all splits.
 
    Scalers are fit only on training data to prevent data leakage.
 
    Returns the six transformed arrays plus (input_scaler, output_scaler) so
    they can be reused at inference time.
    """

    input_scaler = StandardScaler()
    output_scaler = StandardScaler()
 
    input_train_norm = input_scaler.fit_transform(input_train)
    output_train_norm = output_scaler.fit_transform(output_train)
 
    input_val_norm = input_scaler.transform(input_val)
    output_val_norm = output_scaler.transform(output_val)
 
    input_test_norm = input_scaler.transform(input_test)
    output_test_norm = output_scaler.transform(output_test)
 
    return (
        input_train_norm, output_train_norm,
        input_val_norm, output_val_norm,
        input_test_norm, output_test_norm,
        input_scaler, output_scaler,
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
        flatten: bool
    ) -> tuple:
    """
    Converts raw data in the form of lists of (dataframes or dicts of dataframes) into data for machine learning. 
    The resulting data is normalized and in the form of tensors.

    The returned data is in the form of a tuple consisting of:
    (input training dataset, output training dataset, 
    input validation data, output validation dataset, 
    input test dataset, output test dataset, 
    input scaler, output scaler)
    """
    
    input_train_numpy = convert_dataframe_to_numpy(input_training_data, flatten)
    output_train_numpy = convert_dataframe_to_numpy(output_training_data, flatten)
    input_val_numpy = convert_dataframe_to_numpy(input_validation_data, flatten)
    output_val_numpy = convert_dataframe_to_numpy(output_validation_data, flatten)
    input_test_numpy = convert_dataframe_to_numpy(input_test_data, flatten)
    output_test_numpy = convert_dataframe_to_numpy(output_test_data, flatten)

    (input_train_norm, output_train_norm, 
     input_val_norm, output_val_norm,
     input_test_norm, output_test_norm,
     input_scaler, output_scaler,
    ) = normalize(
        input_train_numpy,
        output_train_numpy,
        input_val_numpy,
        output_val_numpy,
        input_test_numpy,
        output_test_numpy
        )

    input_train_tensor = to_tensor(input_train_norm)
    output_train_tensor = to_tensor(output_train_norm)
    input_val_tensor = to_tensor(input_val_norm)
    output_val_tensor = to_tensor(output_val_norm)
    input_test_tensor = to_tensor(input_test_norm)
    output_test_tensor = to_tensor(output_test_norm)

    return (
        input_train_tensor, output_train_tensor, 
        input_val_tensor, output_val_tensor, 
        input_test_tensor, output_test_tensor, 
        input_scaler, output_scaler
        )