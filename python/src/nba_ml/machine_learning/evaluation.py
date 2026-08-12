from dataclasses import dataclass

import numpy as np
import torch
from scipy import special
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
import math
from pathlib import Path

from .trainer import MetricFunction

@dataclass(frozen=True)
class ValueScale():
    """
    The number line a set of classes sits on, which is what turns a class back into a statistic.

    A class need not be one value. Where it covers a run of them, class_values holds the middle of
    that run, so every figure below is read in the units a reader knows however wide a class is.
    """

    class_values: np.ndarray
    """What each position stands for, shaped (classes,)."""

    actual_values: np.ndarray
    """What actually happened, as recorded, shaped (samples,)."""

    first_value: float
    """The lowest value the first class covers."""

    value_step: int
    """How many whole numbers one class covers."""

    impossible_value: int | None = None
    """A whole number the statistic cannot take, which is therefore not on the line at all."""

    def lines(self, classes: int) -> np.ndarray:
        """
        Every whole number the range holds, which is every line a model can be asked about.

        A value that cannot happen is not one of them, so the numbers above it shift down onto the
        ones the model does answer with and every class still covers value_step of them.
        """

        lines = self.first_value + np.arange(classes * self.value_step)

        if self.impossible_value is None:
            return lines

        return np.where(lines >= self.impossible_value, lines + 1, lines)

# Metrics scored during training, on batches of logits still held as tensors.

def _accuracy(predictions: torch.Tensor, actuals: torch.Tensor) -> float:
    return (predictions.argmax(dim=1) == actuals).float().mean().item()

def _true_class_probability(predictions: torch.Tensor, actuals: torch.Tensor) -> float:
    probabilities = torch.softmax(predictions, dim=1)

    return probabilities[torch.arange(len(actuals), device=probabilities.device), actuals].mean().item()

def get_ordinal_classification_metrics(class_values: np.ndarray) -> dict[str, MetricFunction]:
    """
    The metrics worth watching per epoch for a model that predicts a distribution over ordered
    values. Accuracy alone hides how far off a wrong prediction was, so the mean absolute error of
    the distribution's expected value is tracked beside it.

    Args:
        class_values is what each position stands for, so the error reads in the statistic's own
        units rather than in classes. What happened is read as the middle of the class it fell in,
        which is all the labels carry. The finished model is scored against the recorded value.
    """

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
    """
    The metrics worth watching per epoch for a model choosing between categories that have no order.

    Accuracy says almost nothing about a rare outcome, because always answering no scores well, so
    the probability the model gave to what actually happened is tracked beside it.
    """

    return {
        "acc": _accuracy,
        "p(true)": _true_class_probability
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

    Counted in classes, and normalized by how many there are. That makes it a fair reading of how
    well a model orders its own classes, and not a way to compare two models whose classes cover
    different amounts of ground. Use the line score for that.
    """

    n_classes = predicted_probabilities.shape[1]

    predicted_cumulative = np.cumsum(predicted_probabilities, axis=1)
    actual_cumulative = (np.arange(n_classes) >= actuals[:, None]).astype(np.float64)

    return float(np.mean(np.sum((predicted_cumulative - actual_cumulative) ** 2, axis=1)) / max(n_classes - 1, 1))

def calculate_line_ranked_probability_score(
    predicted_probabilities: np.ndarray,
    values: ValueScale
    ) -> float:
    """
    How wrong the chance of going over is, added up over every whole number line the range holds.

    This is the one figure that compares two models whose classes cover different amounts of ground.
    A class covering three points is read as spread evenly over those three, which is how the site
    reads one, so both models are asked the same question at every line: what are the odds here.

    Added up rather than averaged, because a line out in the tail scores almost nothing either way.
    Averaging would hand a quiet reward to whichever model was given the wider range, since the extra
    lines are the easy ones. Lower is better.
    """

    classes = predicted_probabilities.shape[1]
    per_value = np.repeat(predicted_probabilities, values.value_step, axis=1) / values.value_step
    lines = values.lines(classes)

    # The chance of landing at or below each line, against whether it actually did.
    predicted_cumulative = np.cumsum(per_value, axis=1)
    happened = (values.actual_values[:, None] <= lines).astype(np.float64)

    return float(np.mean(np.sum((predicted_cumulative - happened) ** 2, axis=1)))

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
"""
How often an outcome has to have happened, per bin, before a reliability diagram of it means
anything.

An outcome at the far end of a range happens a handful of times or never. Its curve is then drawn
from almost no events, on an axis scaled to the noise floor, and reads as wild miscalibration when
the model is doing nothing wrong. Those outcomes are left out rather than drawn.
"""

def plot_calibration(
        predicted_probabilities: np.ndarray,
        actuals: np.ndarray,
        label: str,
        class_labels: list[str],
        n_bins: int = 7,
        rows_columns: int = 3,
        save_graph_directory_path: Path | None = None
        ):
    """
    Plots one reliability diagram per outcome, which shows whether a predicted probability happens as
    often as it claims.

    Args:
        predicted_probabilities is shaped (samples, classes) and actuals holds one class per sample.
        class_labels names what each position stands for, so a graph is titled with the outcome
        rather than with its position, which are not the same wherever a range does not start at zero.
        rows_columns is how many graphs fit across and down one page.
    """

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
        actuals: np.ndarray,
        values: ValueScale
    ) -> dict[str, float]:
    """
    Scores the predicted distributions two ways: by the single class each one favours, and by the
    average value each one implies. The second is the fairer measure of a distribution.

    Both are measured in the statistic's own units, against what was recorded rather than against
    the class it fell in, so a model whose classes are buckets pays for the ground a bucket covers.
    """

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
        class_labels: list[str],
        values: ValueScale | None,
        output_size: int,
        save_graph_directory_path: Path | None
    ):
    """
    Draws a handful of finished distributions, each against the outcomes it is over.

    Args:
        values is the number line the classes sit on, or None when the positions are named
        categories. A category set has no number line, so nothing is averaged across one and no
        expected value is marked.
    """

    sample_size = min(output_size, len(predicted_probabilities))
    indices = np.random.choice(len(predicted_probabilities), size=sample_size, replace=False)

    # Bars sit at the value they stand for, so a range that does not start at zero, or whose classes
    # are wider than one, is drawn as the values a reader knows rather than as positions in an array.
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

def output_test_evaluation_classification(
        predictions: np.ndarray,
        actuals: np.ndarray,
        label: str,
        class_labels: list[str],
        values: ValueScale | None = None,
        output_size: int = 5,
        save_graph_directory_path: Path | None = None
    ) -> dict[str, float]:
    """
    Scores a finished model's predictions and graphs them.

    The figures that need no number line are worked out over positions in the array, which is where
    the model answers. Everything else is read in the statistic's own units, because a report is read
    by somebody who knows the statistic and not the array. The graphs are drawn the same way.

    Args:
        predictions are the model's logits, and actuals the class that happened.
        class_labels names what each position stands for.
        values is the number line the classes sit on, or None when the positions are named
        categories rather than a run of values. Several of the metrics read the positions as a line,
        so they are only scored when there is one.
        save_graph_directory_path saves the graphs there instead of showing them.

    Returns:
        Every metric that was scored, so it can be recorded alongside the model.
    """

    predicted_probabilities = special.softmax(predictions, axis=1)

    metrics: dict[str, float] = {
        "accuracy": float(np.mean(np.argmax(predicted_probabilities, axis=1) == actuals)),
        "mean probability of correct class": float(np.mean(predicted_probabilities[np.arange(len(actuals)), actuals])),
        "brier score": calculate_brier_score(predicted_probabilities, actuals)
    }

    # These read the classes as a line, so none of them says anything about named categories.
    if values is not None:
        metrics["ranked probability score"] = calculate_ranked_probability_score(predicted_probabilities, actuals)
        metrics["ranked probability score over lines"] = calculate_line_ranked_probability_score(
            predicted_probabilities, values
        )
        metrics.update(calculate_classification_ordinal_errors(predicted_probabilities, actuals, values))

    print(f"\n===== SCORES FOR {label.upper()} =====")
    for name, value in metrics.items():
        print(f"{name}: {value:.6f}")

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

    return metrics
