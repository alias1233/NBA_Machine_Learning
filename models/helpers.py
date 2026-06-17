import torch
from pathlib import Path
import numpy as np

def save_dictionary_data_to_file(file_path: str, model_data: list[dict] | dict):
    directory_path = file_path.rpartition('/')[0]

    save_data = {}
    if isinstance(model_data, list):
        for dict in model_data:
            save_data.update(dict)

    else:
        save_data = model_data

    save_model_path = Path(directory_path)
    save_model_path.mkdir(parents=True, exist_ok=True)
    torch.save(save_data, file_path)

def output_test_evaluation(
        predictions: np.ndarray,
        actuals: np.ndarray,
        output_size: int = 15,
        labels: list[str] | None = None
    ):
    """
    Prints out information about the predicted values and the actual values of a model.

    Args:
        labels are an option argument that consists of a list of category names which correspond 
        to each output data point in the order of the model output.
    """

    print("\n===== TEST RESULTS =====")

    mae = np.mean(np.abs(predictions - actuals), axis=0)
    rmse = np.sqrt(np.mean((predictions - actuals) ** 2, axis=0))

    if labels:
        for index, category in enumerate(labels):
            print(f"{category} MAE : {mae[index]}")
        
        for index, category in enumerate(labels):
            print(f"{category} RMSE: {rmse[index]}")
    else:
        for index, data in enumerate(mae):
            print(f'{index} MAE : {data}')

        for index, data in enumerate(rmse):
            print(f'{index} RMSE : {data}')

    print("\n===== SAMPLE PREDICTIONS =====")

    sample_size = min(output_size, len(predictions))
    indices = np.random.choice(len(predictions), size=sample_size, replace=False)

    if labels:
        for idx in indices:
            predicted = predictions[idx]
            actual = actuals[idx]

            print(f"Sample {idx}: ")

            print("Predicted: ")
            for index, category in enumerate(labels):
                print(f"{category}: {predicted[index]}")

            print("Actual: ")
            for index, category in enumerate(labels):
                print(f"{category}: {actual[index]} ")
    
    else:
        for idx in indices:
            predicted = predictions[idx]
            actual = actuals[idx]

            print(f"Sample {idx}: ")

            print("Predicted: ")
            for index, data in enumerate(predicted):
                print(f"{index}: {data} ")

            print("Actual: ")
            for index, data in enumerate(actual):
                print(f"{index}: {data} ")

def print_dataset(dataset, num_to_print):
    for index, data in enumerate(dataset):
        print(data)

        if index >= num_to_print:
            break

def print_datasets(datasets, num_to_print = 0, print_values = True, print_lengths = True):
    for dataset in datasets:
        if print_values:
            try:
                print_dataset(dataset, num_to_print)
            except:
                pass
        
        if print_lengths:
            try:
                print(f"Number of data chunks: {len(dataset)}")
            except:
                pass