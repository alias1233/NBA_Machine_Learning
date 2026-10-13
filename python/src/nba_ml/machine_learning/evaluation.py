from dataclasses import dataclass

import numpy as np
import torch
import math
from pathlib import Path

from .trainer import MetricFunction

# Matplotlib is imported inside the plotting functions so the API never has to load it.

# Metric keys used in saved evaluation files.
LOSS = "loss"
CROSS_ENTROPY = "cross_entropy"
ACCURACY = "accuracy"
PROBABILITY_OF_ACTUAL = "probability_of_actual"
BRIER_SCORE = "brier_score"
CALIBRATION_ERROR = "calibration_error"
CLASSWISE_CALIBRATION_ERROR = "classwise_calibration_error"
RANKED_PROBABILITY_SCORE = "ranked_probability_score"
LINE_RANKED_PROBABILITY_SCORE = "line_ranked_probability_score"
EXPECTED_VALUE_MAE = "expected_value_mae"
EXPECTED_VALUE_RMSE = "expected_value_rmse"
EXPECTED_VALUE_MEDIAN_ERROR = "expected_value_median_error"
HIGHEST_PROBABILITY_MAE = "highest_probability_mae"
HIGHEST_PROBABILITY_RMSE = "highest_probability_rmse"
CENTRAL_INTERVAL_CALIBRATION_ERROR = "central_interval_calibration_error"

CENTRAL_INTERVAL = 0.8
"""Size of the central prediction interval used for the interval calibration metric."""

@dataclass(frozen=True)
class ValueScale():
    """Maps a model's classes to the numeric values they cover."""

    class_values: np.ndarray
    """The value each class represents. Shape: (classes,)."""

    actual_values: np.ndarray
    """The actual value of each sample. Shape: (samples,)."""

    first_value: float
    """Lowest value covered by the first class."""

    value_step: int
    """Number of integers each class covers."""

    impossible_value: int | None = None
    """An integer the stat can never be, e.g. a point differential of 0."""

    def lines(self, classes: int) -> np.ndarray:
        """Returns every integer in the model's range. Each one is a possible over/under line."""

        lines = self.first_value + np.arange(classes * self.value_step)

        if self.impossible_value is None:
            return lines

        return np.where(lines >= self.impossible_value, lines + 1, lines)

    def spread_over_values(self, predicted_probabilities: np.ndarray) -> np.ndarray:
        """Converts class probabilities to a probability per integer, split evenly within each class."""

        return np.repeat(predicted_probabilities, self.value_step, axis=1) / self.value_step

# Metrics computed during training on batches of logits.

def _accuracy(predictions: torch.Tensor, actuals: torch.Tensor) -> float:
    return (predictions.argmax(dim=1) == actuals).float().mean().item()

def _true_class_probability(predictions: torch.Tensor, actuals: torch.Tensor) -> float:
    probabilities = torch.softmax(predictions, dim=1)

    return probabilities[torch.arange(len(actuals), device=probabilities.device), actuals].mean().item()

def get_ordinal_classification_metrics(class_values: np.ndarray) -> dict[str, MetricFunction]:
    """Returns the per-epoch metrics for models that predict a distribution over ordered values."""

    values = torch.as_tensor(class_values, dtype=torch.float32)

    def expected_value_mae(predictions: torch.Tensor, actuals: torch.Tensor) -> float:
        scale = values.to(device=predictions.device, dtype=predictions.dtype)
        expected_values = (torch.softmax(predictions, dim=1) * scale).sum(dim=1)

        return (expected_values - scale[actuals]).abs().mean().item()

    return {
        "acc": _accuracy,
        "mae": expected_value_mae
    }

def get_classification_metrics() -> dict[str, MetricFunction]:
    """Returns the per-epoch metrics for models that predict unordered categories."""

    return {
        "acc": _accuracy,
        "p(true)": _true_class_probability
    }

# Metrics computed after training on the full set of predictions.

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
    """Returns the mean squared error between the predicted probabilities and the one-hot outcome."""

    one_hot_actuals = np.zeros_like(predicted_probabilities)
    one_hot_actuals[np.arange(len(actuals)), actuals] = 1.0

    return float(np.mean(np.sum((predicted_probabilities - one_hot_actuals) ** 2, axis=1)))

def calculate_ranked_probability_score(
    predicted_probabilities: np.ndarray,
    actuals: np.ndarray
    ) -> float:
    """Like the Brier score, but computed on cumulative probabilities so the class order matters."""

    n_classes = predicted_probabilities.shape[1]

    predicted_cumulative = np.cumsum(predicted_probabilities, axis=1)
    actual_cumulative = (np.arange(n_classes) >= actuals[:, None]).astype(np.float64)

    return float(np.mean(np.sum((predicted_cumulative - actual_cumulative) ** 2, axis=1)) / max(n_classes - 1, 1))

def calculate_line_ranked_probability_score(
    predicted_probabilities: np.ndarray,
    values: ValueScale
    ) -> float:
    """Ranked probability score computed over every integer line instead of every class."""

    classes = predicted_probabilities.shape[1]
    lines = values.lines(classes)

    # Predicted probability of finishing at or below each line, compared with what happened.
    predicted_cumulative = np.cumsum(values.spread_over_values(predicted_probabilities), axis=1)
    happened = (values.actual_values[:, None] <= lines).astype(np.float64)

    return float(np.mean(np.sum((predicted_cumulative - happened) ** 2, axis=1)))

def calculate_central_interval_calibration_error(
    predicted_probabilities: np.ndarray,
    values: ValueScale,
    interval: float = CENTRAL_INTERVAL
    ) -> float:
    """Returns the difference between how often the central interval contained the result and its predicted probability."""

    classes = predicted_probabilities.shape[1]
    lines = values.lines(classes)
    cumulative = np.cumsum(values.spread_over_values(predicted_probabilities), axis=1)

    tail = (1.0 - interval) / 2.0
    lowest_positions = np.argmax(cumulative >= tail, axis=1)
    highest_positions = np.argmax(cumulative >= 1.0 - tail, axis=1)
    lowest = lines[lowest_positions]
    highest = lines[highest_positions]

    inside = (values.actual_values >= lowest) & (values.actual_values <= highest)
    rows = np.arange(len(predicted_probabilities))
    expected = cumulative[rows, highest_positions]
    expected -= np.where(
        lowest_positions > 0,
        cumulative[rows, np.maximum(lowest_positions - 1, 0)],
        0.0
    )

    return abs(float(np.mean(inside)) - float(np.mean(expected)))

def class_prior(outputs: np.ndarray, classes: int) -> np.ndarray:
    """Returns the frequency of each class, used as a baseline prediction."""

    counts = np.bincount(np.asarray(outputs, dtype=np.int64), minlength=classes).astype(np.float64)
    total = counts.sum()

    return counts / total if total else np.full(classes, 1.0 / classes)

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

OCCURRENCES_PER_BIN = 5
"""Minimum occurrences per bin for an outcome to get a reliability diagram."""

def plot_calibration(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray,
        label: str,
        class_labels: list[str],
        n_bins: int = 7,
        rows_columns: int = 3,
        save_graph_directory_path: Path | None = None
        ):
    """Plots one reliability diagram per outcome."""

    import matplotlib.pyplot as plt
    from sklearn.calibration import calibration_curve

    occurrences = np.bincount(actuals, minlength=predicted_probabilities.shape[1])
    drawn = [
        position for position, count in enumerate(occurrences)
        if count >= n_bins * OCCURRENCES_PER_BIN
    ]

    if not drawn:
        print(f"No outcome of {label} happened often enough to plot a reliability diagram of.")
        return

    classes_per_page = rows_columns * rows_columns
    n_pages = math.ceil(len(drawn) / classes_per_page)

    if save_graph_directory_path is not None:
        save_graph_directory_path.mkdir(parents=True, exist_ok=True)

    for page in range(n_pages):
        page_classes = drawn[page * classes_per_page : (page + 1) * classes_per_page]

        figure, axes = plt.subplots(
            rows_columns,
            rows_columns,
            figsize=(5 * rows_columns, 4 * rows_columns),
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
            combined_min = min(prob_pred.min(), prob_true.min())
            combined_max = max(prob_pred.max(), prob_true.max())
            margin = (combined_max - combined_min) * pad or pad

            lo = max(-0.05, combined_min - margin)
            hi = min(1.05, combined_max + margin)

            axes[i].plot([lo, hi], [lo, hi], linestyle='--', color='gray', label='Perfect')

            axes[i].set_xlim(lo, hi)
            axes[i].set_ylim(lo, hi)

            axes[i].set_title(f'{class_labels[class_idx]} ({occurrences[class_idx]:,} times)')
            axes[i].set_xlabel('Predicted Probability')
            axes[i].set_ylabel('Actual Frequency')
            axes[i].legend()

        for i in range(len(page_classes), len(axes)):
            axes[i].set_visible(False)

        plt.suptitle(
            f'{label} calibration, page {page + 1} of {n_pages} '
            f'({class_labels[page_classes[0]]} to {class_labels[page_classes[-1]]}). '
            f'{len(drawn)} of {len(occurrences)} outcomes happened often enough to draw.'
        )
        plt.tight_layout(rect=(0, 0, 1, 0.96))

        if save_graph_directory_path is not None:
            figure.savefig(save_graph_directory_path / f"{label}_calibration_{page}.png")

        else:
            plt.show()

        plt.close(figure)

def calculate_classification_ordinal_errors(
        predicted_probabilities: np.ndarray,
        values: ValueScale
    ) -> dict[str, float]:
    """Returns error metrics for the most likely value and the expected value of each prediction."""

    highest_probability_mae, highest_probability_rmse = calculate_mae_and_rmse_error(
        values.class_values[np.argmax(predicted_probabilities, axis=1)],
        values.actual_values
    )

    expected_values = np.sum(predicted_probabilities * values.class_values, axis=1)
    expected_value_mae, expected_value_rmse = calculate_mae_and_rmse_error(
        expected_values,
        values.actual_values
    )

    return {
        HIGHEST_PROBABILITY_MAE: float(highest_probability_mae[0]),
        HIGHEST_PROBABILITY_RMSE: float(highest_probability_rmse[0]),
        EXPECTED_VALUE_MAE: float(expected_value_mae[0]),
        EXPECTED_VALUE_RMSE: float(expected_value_rmse[0]),
        EXPECTED_VALUE_MEDIAN_ERROR: float(np.median(np.abs(expected_values - values.actual_values)))
    }

def _plot_predicted_distributions(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray,
        label: str,
        class_labels: list[str],
        values: ValueScale | None,
        output_size: int,
        save_graph_directory_path: Path | None
    ):
    """Plots a random sample of predicted distributions."""

    import matplotlib.pyplot as plt

    sample_size = min(output_size, len(predicted_probabilities))
    indices = np.random.choice(len(predicted_probabilities), size=sample_size, replace=False)

    positions = (
        np.arange(predicted_probabilities.shape[1]) if values is None else values.class_values
    )
    bar_width = 0.8 if values is None else 0.8 * values.value_step

    if save_graph_directory_path is not None:
        save_graph_directory_path.mkdir(parents=True, exist_ok=True)

    for loop_count, idx in enumerate(indices):
        probabilities = predicted_probabilities[idx]
        actual_position = int(actuals[idx])

        figure = plt.figure(figsize=(10, 4))
        plt.bar(positions, probabilities, width=bar_width, color='black')

        if values is None:
            plt.axvline(
                x=positions[actual_position],
                color='red',
                linestyle='-',
                linewidth=2,
                label=f'Actual: {class_labels[actual_position]}'
            )
            plt.xticks(positions, class_labels)
        else:
            actual_value = float(values.actual_values[idx])
            plt.axvline(
                x=actual_value,
                color='red',
                linestyle='-',
                linewidth=2,
                label=f'Actual: {actual_value:g}'
            )

            expected_value = float(np.sum(probabilities * positions))
            plt.axvline(
                x=expected_value,
                color='green',
                linestyle='-',
                linewidth=2,
                label=f'Expected value: {expected_value:.2f}'
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

def score_classification(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray,
        values: ValueScale | None = None
    ) -> dict[str, float]:
    """Returns every evaluation metric for the predictions, keyed by the metric keys above."""

    metrics: dict[str, float] = {
        ACCURACY: float(np.mean(np.argmax(predicted_probabilities, axis=1) == actuals)),
        PROBABILITY_OF_ACTUAL: float(
            np.mean(predicted_probabilities[np.arange(len(actuals)), actuals])
        ),
        BRIER_SCORE: calculate_brier_score(predicted_probabilities, actuals),
        CALIBRATION_ERROR: expected_calibration_error_top_label(predicted_probabilities, actuals),
        CLASSWISE_CALIBRATION_ERROR: expected_calibration_error_classwise(
            predicted_probabilities, actuals
        )
    }

    # These metrics need ordered numeric classes, so they are skipped for category outputs.
    if values is not None:
        metrics[RANKED_PROBABILITY_SCORE] = calculate_ranked_probability_score(
            predicted_probabilities, actuals
        )
        metrics[LINE_RANKED_PROBABILITY_SCORE] = calculate_line_ranked_probability_score(
            predicted_probabilities, values
        )
        metrics[CENTRAL_INTERVAL_CALIBRATION_ERROR] = calculate_central_interval_calibration_error(
            predicted_probabilities, values
        )
        metrics.update(calculate_classification_ordinal_errors(predicted_probabilities, values))

    return metrics

def graph_classification(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray,
        label: str,
        class_labels: list[str],
        values: ValueScale | None = None,
        output_size: int = 5,
        save_graph_directory_path: Path | None = None
    ):
    """Plots a sample of predicted distributions and a reliability diagram for each outcome."""

    _plot_predicted_distributions(
        predicted_probabilities,
        actuals,
        label,
        class_labels,
        values,
        output_size,
        save_graph_directory_path
    )

    plot_calibration(
        predicted_probabilities,
        actuals,
        label,
        class_labels,
        save_graph_directory_path=save_graph_directory_path
        )
