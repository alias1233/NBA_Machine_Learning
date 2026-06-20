import torch
from pathlib import Path
import numpy as np
from scipy import special
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
import math
import os

def get_best_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

def load_dictionary_data_from_file(file_path: str) -> dict:
    return torch.load(file_path, weights_only=False)

def save_dictionary_data_to_file(file_path: str, model_data: list[dict] | dict):
    directory_path = file_path.rpartition('/')[0]

    save_data = {}
    if isinstance(model_data, list):
        for d in model_data:
            save_data.update(d)

    else:
        save_data = model_data

    save_model_path = Path(directory_path)
    save_model_path.mkdir(parents=True, exist_ok=True)
    torch.save(save_data, file_path)

# Logging Evaluations

# TODO: Add brier error aswell

def expected_calibration_error(
    predicted_probabilities: np.ndarray,
    actuals: np.ndarray,
    n_bins: int = 7
    ):
    confidences = predicted_probabilities.max(axis=1)
    predictions = predicted_probabilities.argmax(axis=1)
    correctness = (predictions == actuals)

    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        if i == n_bins - 1:
            in_bin = (confidences >= bins[i]) & (confidences <= bins[i + 1])
        else:
            in_bin = (confidences >= bins[i]) & (confidences < bins[i + 1])

        if not np.any(in_bin):
            continue

        accuracy = correctness[in_bin].mean()
        confidence = confidences[in_bin].mean()

        ece += (in_bin.sum() / len(actuals)) * abs(accuracy - confidence)

    return float(ece)

def plot_calibration(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray,
        label: str,
        n_bins: int = 7,
        rows_columns: int = 3,
        save_graph_directory_path: str | None = None
        ):
    """
    For each class, plot a reliability diagram, paginated across multiple figures.
    predicted_probabilities: shape (n_samples, n_classes)
    actuals: shape (n_samples,) with integer class labels
    row_columns: Num of rows and columns of graphs per page
    """
    
    n_classes = predicted_probabilities.shape[1]
    n_cols = rows_columns
    n_rows = rows_columns
    classes_per_page = rows_columns * rows_columns
    n_pages = math.ceil(n_classes / classes_per_page)

    if save_graph_directory_path is not None:
        os.makedirs(save_graph_directory_path, exist_ok=True)

    for page in range(n_pages):
        start = page * classes_per_page
        end = min(start + classes_per_page, n_classes)
        page_classes = list(range(start, end))
        n_on_page = len(page_classes)

        fig, axes = plt.subplots(
            n_rows,
            n_cols,
            figsize=(5 * n_cols, 4 * n_rows),
            squeeze=False
        )
        axes = axes.flatten()

        for i, class_idx in enumerate(page_classes):
            binary_actuals = (actuals == class_idx).astype(int)
            class_probs = predicted_probabilities[:, class_idx]

            prob_true, prob_pred = calibration_curve(
                binary_actuals, class_probs, n_bins=n_bins, strategy='quantile'
            )

            axes[i].plot(prob_pred, prob_true, marker='o', label='Model')

            pad = 0.25
            x_min, x_max = prob_pred.min(), prob_pred.max()
            y_min, y_max = prob_true.min(), prob_true.max()
            combined_min = min(x_min, y_min)
            combined_max = max(x_max, y_max)
            margin = (combined_max - combined_min) * pad or pad

            lo = max(-0.05, combined_min - margin)
            hi = min(1.05, combined_max + margin)

            axes[i].plot([lo, hi], [lo, hi], linestyle='--', color='gray', label='Perfect')

            axes[i].set_xlim(lo, hi)
            axes[i].set_ylim(lo, hi)

            axes[i].set_title(f'Class {class_idx}')
            axes[i].set_xlabel('Predicted Probability')
            axes[i].set_ylabel('Actual Frequency')
            axes[i].legend()

        # Hide unused subplots on the last page
        for i in range(n_on_page, len(axes)):
            axes[i].set_visible(False)

        plt.suptitle(f'Calibration Curves — Page {page + 1} of {n_pages} (Classes {start}–{end - 1})')
        plt.tight_layout(rect=(0, 0, 1, 0.96))

        if save_graph_directory_path is not None:
            plt.savefig(save_graph_directory_path.rstrip('/') + "/" + label + "_calibration_" + str(page) + ".png")
            plt.close()

        else:
            plt.show()

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

    ece = expected_calibration_error(
        predicted_probabilities,
        actuals
    )
    print(f"Expected Calibration Error: {ece}")

    print("\n===== SAMPLE PREDICTIONS =====")

    sample_size = min(output_size, len(predicted_probabilities))
    indices = np.random.choice(len(predicted_probabilities), size=sample_size, replace=False)

    if save_graph_directory_path is not None:
        os.makedirs(save_graph_directory_path, exist_ok=True)

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
            plt.savefig(save_graph_directory_path.rstrip('/') + "/" + label + "_distribution_" + str(loop_count) + ".png")
            plt.close()
        
        else:
            plt.show()
    
    plot_calibration(
        predicted_probabilities, 
        actuals, 
        label,
        save_graph_directory_path=save_graph_directory_path
        )

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

# Logging helpers
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