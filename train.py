from datetime import datetime
import pandas as pd
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler

from src.data_preparation.data_preprocessing import player_props_processing
from src.training.trainer import Trainer
from src.training.models.feed_forward import FeedForward

RANDOM_SEED = 1

torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

CHUNK_STEP_SIZE = 1
VALIDATION_START_DATE = datetime(2026, 1, 1)
TEST_START_DATE = datetime(2026, 3, 1)

HIDDEN_LAYERS = [
    40,
    20,
    10,
]

LEARNING_RATE = 0.001
EPOCHS = 500
LOSS_FUNCTION = torch.nn.MSELoss()
SAVE_MODEL_FILE_PATH = 'trained_models/test.pth'
LOG_LOSS_INTERVAL = 10

def print_dataset(dataset, num_to_print):
    for index, data in enumerate(dataset):
        print(data)

        if index > num_to_print:
            break
    
    print(f"NUM CHUNKS: {len(dataset)}")

def print_datasets(datasets, num_to_print = 0, print_values = True, print_lengths = True):
    if print_values:
        import pandas as pd
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    for dataset in datasets:
        if print_values:
            print_dataset(dataset, num_to_print)
        
        if print_lengths:
            print(f"NUM CHUNKS: {len(dataset)}")

def squisher_and_cleaner(data: list[dict[str, pd.DataFrame]] | list[pd.DataFrame] | list[pd.Series]) -> np.ndarray:
    """
    Squishes the given data into a format that can be easily used for normalization and training.

    Each element in the list should correspond to 1 dimensional structure of features for training with a simple Feed Forward model. 
    """
    
    samples = []

    for chunk in data:
        if isinstance(chunk, dict):
            flattened_arrays = []

            for _, dataframe in chunk.items():
                try:
                    flattened_arrays.append(dataframe.to_numpy(dtype=np.float32).reshape(-1))
                except Exception as e:
                    print(e)
                    print(dataframe)

            samples.append(np.concatenate(flattened_arrays))

        elif isinstance(chunk, pd.DataFrame) | isinstance(chunk, pd.Series):
            samples.append(chunk.to_numpy(dtype=np.float32).reshape(-1))

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
    
def train(debug: bool = False):
    datasets = player_props_processing.get_all_player_props_input_output_training_data(
        validation_split_start_date = VALIDATION_START_DATE,
        test_split_start_date = TEST_START_DATE,
        chunk_step_size = CHUNK_STEP_SIZE,
        print_debug = True
        )
    
    if debug:
        print_datasets(datasets, 1, False, True)
    
    cleaned_datasets = [squisher_and_cleaner(ds) for ds in datasets]
 
    input_train_clean, output_train_clean, input_val_clean, output_val_clean, input_test_clean, output_test_clean = cleaned_datasets
 
    if debug:
        print(f"Input feature dimensions: {input_train_clean.shape}")
        print(f"Output feature dimensions: {output_train_clean.shape}")
 
    (input_train_norm, output_train_norm, 
     input_val_norm, output_val_norm,
     input_test_norm, output_test_norm,
     input_scaler, output_scaler,
    ) = normalize(
        input_train_clean, output_train_clean,
        input_val_clean, output_val_clean,
        input_test_clean, output_test_clean,
    )
 
    input_train_tensor = to_tensor(input_train_norm)
    output_train_tensor = to_tensor(output_train_norm)
    input_val_tensor = to_tensor(input_val_norm)
    output_val_tensor = to_tensor(output_val_norm)

    in_features = input_train_tensor.shape[1]
    out_features = output_train_tensor.shape[1]

    model = FeedForward(
        in_features,
        out_features,
        HIDDEN_LAYERS
    )

    trainer = Trainer(
        LEARNING_RATE,
        model
    )

    trainer.train(
        EPOCHS,
        input_train_tensor,
        output_train_tensor,
        input_val_tensor,
        output_val_tensor,
        LOSS_FUNCTION,
        SAVE_MODEL_FILE_PATH,
        LOG_LOSS_INTERVAL
    )

    # TODO: Use test dataset to do a final evaluation

if __name__ == '__main__':
    train(True)