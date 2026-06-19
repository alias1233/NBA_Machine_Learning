import torch
from pathlib import Path
import numpy as np
from scipy import special
import matplotlib.pyplot as plt
import os

def get_best_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

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

def output_test_evaluation_classification(
        predictions: np.ndarray,
        actuals: np.ndarray,
        label: str,
        output_size: int = 5,
        save_graph_directory_path: str | None = None
    ):
    """
    Graphs information about the predicted classification and the actual classifications of model predictions.

    Args:
        predictions should be the outputted logits of the model.
        actuals should be the true classification of the values. 
        save_graph_directory_path if set is a string path to a directory to save the evaluation graphs to.
    """

    print("\n===== TEST RESULTS =====")

    predicted_probabilities = special.softmax(predictions, axis=1)

    highest_probability_predictions = np.argmax(predicted_probabilities, axis=1)

    mae = np.mean(np.abs(highest_probability_predictions - actuals), axis=0)
    rmse = np.sqrt(np.mean((highest_probability_predictions - actuals) ** 2, axis=0))

    print("Highest Probabilty Predictions:")
    print(f'MAE: {mae}')
    print(f'RMSE: {rmse}')

    class_indices = np.arange(predicted_probabilities.shape[1])
    expected_values = np.sum(predicted_probabilities * class_indices, axis=1)

    mae = np.mean(np.abs(expected_values - actuals), axis=0)
    rmse = np.sqrt(np.mean((expected_values - actuals) ** 2, axis=0))

    print("Expected Probability Predictions:")
    print(f'MAE: {mae}')
    print(f'RMSE: {rmse}')

    print("\n===== SAMPLE PREDICTIONS =====")

    sample_size = min(output_size, len(predicted_probabilities))
    indices = np.random.choice(len(predicted_probabilities), size=sample_size, replace=False)

    for loop_count, idx in enumerate(indices):
        probabilities = predicted_probabilities[idx]
        actual_value = actuals[idx].item()
        expected_value = np.sum(probabilities * class_indices).item()

        plt.figure(figsize=(10, 4))
        plt.bar(
            range(len(probabilities)),
            probabilities,
            color='black'
            )
        
        plt.axvline(
            x=actual_value,
            color='red',
            linestyle='-',
            linewidth=2,
            label=f'Actual: {actual_value}'
        )

        plt.axvline(
            x=expected_value,
            color='green',
            linestyle='-',
            linewidth=2,
            label=f'Expected Value: {expected_value}'
        )

        plt.legend()
        plt.xlabel(label)
        plt.ylabel("Probability")
        plt.title(f"Predicted Distribution For Index: {idx}")

        if save_graph_directory_path is not None:
            os.makedirs(save_graph_directory_path, exist_ok=True)

            plt.savefig(save_graph_directory_path + "/" + label + "_" + str(loop_count) + ".png")
            plt.close()
        
        else:
            plt.show()

def output_test_evaluation_regression(
        predictions: np.ndarray,
        actuals: np.ndarray,
        output_size: int = 15,
        labels: list[str] | None = None
    ):
    """
    Prints out information about the predicted values and the actual values of model predictions.

    Args:
        labels are an optional argument that consists of a list of category names which correspond 
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