import numpy as np
import torch
from scipy import special
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
import math
from pathlib import Path

from .trainer import MetricFunction

# Metrics scored during training, on batches of logits still held as tensors.

def _accuracy(predictions: torch.Tensor, actuals: torch.Tensor) -> float:
    return (predictions.argmax(dim=1) == actuals).float().mean().item()

def _expected_value_mae(predictions: torch.Tensor, actuals: torch.Tensor) -> float:
    probabilities = torch.softmax(predictions, dim=1)
    class_indices = torch.arange(predictions.shape[1], device=predictions.device, dtype=probabilities.dtype)
    expected_values = (probabilities * class_indices).sum(dim=1)

    return (expected_values - actuals).abs().mean().item()

def get_ordinal_classification_metrics() -> dict[str, MetricFunction]:
    """
    The metrics worth watching per epoch for a model that predicts a distribution over ordered
    whole numbers. Accuracy alone hides how far off a wrong prediction was, so the mean absolute
    error of the distribution's expected value is tracked beside it.
    """

    return {
        "acc": _accuracy,
        "mae": _expected_value_mae
    }

# Metrics scored after training, on the full set of predictions held as arrays.

def calculate_mae_and_rmse_error(
    predictions: np.ndarray,
    actuals: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:

    mae = np.mean(np.abs(predictions - actuals), axis=0)
    rmse = np.sqrt(np.mean((predictions - actuals) ** 2, axis=0))

    return np.atleast_1d(mae), np.atleast_1d(rmse)

def calculate_brier_score(
    predicted_probabilities: np.ndarray,
    actuals: np.ndarray
    ) -> float:
    """
    The mean squared distance between the predicted distribution and the outcome that happened.
    Lower is better, and unlike accuracy it rewards being confident only when that is warranted.
    """

    one_hot_actuals = np.zeros_like(predicted_probabilities)
    one_hot_actuals[np.arange(len(actuals)), actuals] = 1.0

    return float(np.mean(np.sum((predicted_probabilities - one_hot_actuals) ** 2, axis=1)))

def calculate_ranked_probability_score(
    predicted_probabilities: np.ndarray,
    actuals: np.ndarray
    ) -> float:
    """
    The Brier score's ordered cousin, scored on running totals instead of single classes, so
    putting probability one class away from the outcome costs less than putting it ten away.
    This is the metric that matches what an over/under line asks of the model.

    Normalized by the number of classes so that models with different class counts compare.
    """

    n_classes = predicted_probabilities.shape[1]

    predicted_cumulative = np.cumsum(predicted_probabilities, axis=1)
    actual_cumulative = (np.arange(n_classes) >= actuals[:, None]).astype(np.float64)

    return float(np.mean(np.sum((predicted_cumulative - actual_cumulative) ** 2, axis=1)) / max(n_classes - 1, 1))

def calculate_binary_ece(
    confidences: np.ndarray,
    correctness: np.ndarray,
    n_bins: int
    ) -> float:

    n_samples = len(confidences)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        if i == 0:
            in_bin = (confidences >= bins[i]) & (confidences <= bins[i + 1])
        else:
            in_bin = (confidences > bins[i]) & (confidences <= bins[i + 1])

        if not np.any(in_bin):
            continue

        bin_size = in_bin.sum()
        accuracy = correctness[in_bin].mean()
        confidence = confidences[in_bin].mean()

        ece += (bin_size / n_samples) * abs(accuracy - confidence)

    return float(ece)

def expected_calibration_error_top_label(
    predicted_probabilities: np.ndarray,
    actuals: np.ndarray,
    n_bins: int = 7
    ) -> float:

    confidences = predicted_probabilities.max(axis=1)
    predicted_classes = predicted_probabilities.argmax(axis=1)
    correctness = (predicted_classes == actuals)

    return calculate_binary_ece(
        confidences,
        correctness,
        n_bins
        )

def expected_calibration_error_classwise(
    predicted_probabilities: np.ndarray,
    actuals: np.ndarray,
    n_bins: int = 7
    ) -> float:

    n_classes: int = predicted_probabilities.shape[1]
    total_ece: float = 0.0
    for class_idx in range(n_classes):
        class_confidences = predicted_probabilities[:, class_idx]
        correctness = (actuals == class_idx)

        total_ece += calculate_binary_ece(
            class_confidences,
            correctness,
            n_bins
        )

    return total_ece / n_classes

def plot_calibration(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray,
        label: str,
        n_bins: int = 7,
        rows_columns: int = 3,
        save_graph_directory_path: Path | None = None
        ):
    """
    For each classification, plot a reliability diagram depicted the accuracy of a predicted probability.
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
        save_graph_directory_path.mkdir(parents=True, exist_ok=True)

    for page in range(n_pages):
        start = page * classes_per_page
        end = min(start + classes_per_page, n_classes)
        page_classes = list(range(start, end))
        n_on_page = len(page_classes)

        figure, axes = plt.subplots(
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

        for i in range(n_on_page, len(axes)):
            axes[i].set_visible(False)

        plt.suptitle(f'Calibration Curves — Page {page + 1} of {n_pages} (Classes {start}–{end - 1})')
        plt.tight_layout(rect=(0, 0, 1, 0.96))

        if save_graph_directory_path is not None:
            figure.savefig(save_graph_directory_path / f"{label}_calibration_{page}.png")

        else:
            plt.show()

        plt.close(figure)

def calculate_classification_ordinal_errors(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray
    ) -> dict[str, float]:
    """
    Scores the predicted distributions two ways: by the single class each one favours, and by the
    average value each one implies. The second is the fairer measure of a distribution.
    """

    highest_probability_predictions = np.argmax(predicted_probabilities, axis=1)
    highest_probability_mae, highest_probability_rmse = calculate_mae_and_rmse_error(
        highest_probability_predictions,
        actuals
    )

    class_indices = np.arange(predicted_probabilities.shape[1])
    expected_values = np.sum(predicted_probabilities * class_indices, axis=1)
    expected_value_mae, expected_value_rmse = calculate_mae_and_rmse_error(
        expected_values,
        actuals
    )

    return {
        "highest probability MAE": float(highest_probability_mae[0]),
        "highest probability RMSE": float(highest_probability_rmse[0]),
        "expected value MAE": float(expected_value_mae[0]),
        "expected value RMSE": float(expected_value_rmse[0]),
        "expected calibration error top label": expected_calibration_error_top_label(predicted_probabilities, actuals),
        "expected calibration error classwise": expected_calibration_error_classwise(predicted_probabilities, actuals)
    }

def _plot_predicted_distributions(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray,
        label: str,
        output_size: int,
        save_graph_directory_path: Path | None
    ):

    sample_size = min(output_size, len(predicted_probabilities))
    indices = np.random.choice(len(predicted_probabilities), size=sample_size, replace=False)
    class_indices = np.arange(predicted_probabilities.shape[1])

    if save_graph_directory_path is not None:
        save_graph_directory_path.mkdir(parents=True, exist_ok=True)

    for loop_count, idx in enumerate(indices):
        probabilities = predicted_probabilities[idx]
        actual_value = actuals[idx].item()
        expected_value = np.sum(probabilities * class_indices).item()

        figure = plt.figure(figsize=(10, 4))
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
            figure.savefig(save_graph_directory_path / f"{label}_distribution_{loop_count}.png")

        else:
            plt.show()

        plt.close(figure)

def output_test_evaluation_classification(
        predictions: np.ndarray,
        actuals: np.ndarray,
        label: str,
        ordinal: bool = False,
        output_size: int = 5,
        save_graph_directory_path: Path | None = None
    ) -> dict[str, float]:
    """
    Graphs information about the predicted classification and the actual classifications of model predictions.

    Args:
        predictions are be the outputted logits of the model.
        actuals are the true classification of the values.
        save_graph_directory_path if set is a string path to a directory to save the evaluation graphs to.

    Returns:
        Every metric that was scored, so it can be recorded alongside the model.
    """

    predicted_probabilities = special.softmax(predictions, axis=1)

    metrics: dict[str, float] = {
        "accuracy": float(np.mean(np.argmax(predicted_probabilities, axis=1) == actuals)),
        "mean probability of correct class": float(np.mean(predicted_probabilities[np.arange(len(actuals)), actuals])),
        "brier score": calculate_brier_score(predicted_probabilities, actuals),
        "ranked probability score": calculate_ranked_probability_score(predicted_probabilities, actuals)
    }

    if ordinal:
        metrics.update(calculate_classification_ordinal_errors(predicted_probabilities, actuals))

    print("\n===== TEST RESULTS =====")
    for name, value in metrics.items():
        print(f"{name}: {value:.6f}")

    print("\n===== SAMPLE PREDICTIONS =====")

    _plot_predicted_distributions(
        predicted_probabilities,
        actuals,
        label,
        output_size,
        save_graph_directory_path
    )

    plot_calibration(
        predicted_probabilities,
        actuals,
        label,
        save_graph_directory_path=save_graph_directory_path
        )

    return metrics
