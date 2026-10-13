"""Evaluation metrics: their labels and descriptions, and the saved evaluation of a model."""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import numpy as np

from nba_ml.machine_learning import evaluation
from nba_ml.models.outputs import CategoryDistribution, IntegerDistribution, ModelOutput

class MetricUnit(StrEnum):
    """The unit of a metric."""

    VALUE = "value"
    """In the units of the predicted stat, such as points."""

    PROBABILITY = "probability"
    """A value between 0 and 1, shown as a percentage."""

    SCORE = "score"
    """A unitless number that only means something next to the baseline."""

@dataclass(frozen=True)
class Metric():
    """A metric a model can be evaluated on, with the text shown for it on the site."""

    key: str
    """The metric's key in a saved evaluation file."""

    label: str
    description: str
    """Short explanation of what the metric means."""

    unit: MetricUnit
    higher_is_better: bool
    ideal: float | None = None
    """Target value for metrics where closer to it is better."""

ALL_METRICS: dict[str, Metric] = {
    metric.key: metric
    for metric in (
        Metric(
            evaluation.EXPECTED_VALUE_MAE,
            "Average error",
            "The distance between the model's expected answer and the true outcome, averaged over every "
            "tested game.",
            MetricUnit.VALUE,
            higher_is_better=False
        ),
        Metric(
            evaluation.EXPECTED_VALUE_MEDIAN_ERROR,
            "Typical error",
            "The median error of the expected answer and the truth. Half the predictions were at least "
            "this close, so a handful of outlier games does not affect the metric.",
            MetricUnit.VALUE,
            higher_is_better=False
        ),
        Metric(
            evaluation.EXPECTED_VALUE_RMSE,
            "Root mean squared error",
            "The average error, except it weighs a large miss far more heavily than a minor one.",
            MetricUnit.VALUE,
            higher_is_better=False
        ),
        Metric(
            evaluation.HIGHEST_PROBABILITY_MAE,
            "Error of the single likeliest answer",
            "How far the predicted likeliest outcome landed from what happened.",
            MetricUnit.VALUE,
            higher_is_better=False
        ),
        Metric(
            evaluation.HIGHEST_PROBABILITY_RMSE,
            "Root mean squared error of the likeliest answer",
            "The error of the likeliest answer, weighing a large miss far more heavily than a small one.",
            MetricUnit.VALUE,
            higher_is_better=False
        ),
        Metric(
            evaluation.CENTRAL_INTERVAL_CALIBRATION_ERROR,
            "Interval calibration error",
            "Measures how accurately a model's prediction intervals match the true outcome. If a model "
            "predicts a 90% confidence range, this tracks how much the actual data falls inside that range "
            "versus the expected 90% of the time.",
            MetricUnit.PROBABILITY,
            higher_is_better=False
        ),
        Metric(
            evaluation.ACCURACY,
            "Exact answers",
            "How often the outcome that the model gave the highest probability of occurring was the actual outcome.",
            MetricUnit.PROBABILITY,
            higher_is_better=True
        ),
        Metric(
            evaluation.PROBABILITY_OF_ACTUAL,
            "Chance given to what happened",
            "The average probability the model predicted for the outcome that actually occurred. Higher "
            "is better. This is the metric that matters where one outcome is rare.",
            MetricUnit.PROBABILITY,
            higher_is_better=True
        ),
        Metric(
            evaluation.BRIER_SCORE,
            "Brier score",
            "How far the whole answer was from the true value. It rewards confidence only where the "
            "confidence was warranted.",
            MetricUnit.SCORE,
            higher_is_better=False
        ),
        Metric(
            evaluation.CALIBRATION_ERROR,
            "Calibration error",
            "How far the model's stated confidence is from how often it turns out to be right. "
            "Zero means an answer given a 70% chance happens 70% of the time, which indicates "
            "a perfectly calibrated model.",
            MetricUnit.SCORE,
            higher_is_better=False
        ),
        Metric(
            evaluation.CLASSWISE_CALIBRATION_ERROR,
            "Calibration error across every outcome",
            "A measure of how calibrated the model is, calculated by averaging, over every possible "
            "outcome, how closely the chance the model gave that outcome matched how often it actually "
            "occurred.",
            MetricUnit.SCORE,
            higher_is_better=False
        ),
        Metric(
            evaluation.LINE_RANKED_PROBABILITY_SCORE,
            "Line score",
            "The error in the predicted chance of the outcome surpassing a line against the actual "
            "probability the outcome surpassed a line, added up over every possible line. This metric "
            "can compare models whose answers cover different intervals.",
            MetricUnit.SCORE,
            higher_is_better=False
        ),
        Metric(
            evaluation.RANKED_PROBABILITY_SCORE,
            "Ranked probability score",
            "Measures the distance between the predicted outcome and the true value, penalizing closer "
            "predictions less than further ones.",
            MetricUnit.SCORE,
            higher_is_better=False
        ),
        Metric(
            evaluation.CROSS_ENTROPY,
            "Log loss",
            "What the model was fitted to reduce. Lower means more of the answer sat on what "
            "happened.",
            MetricUnit.SCORE,
            higher_is_better=False
        ),
        Metric(
            evaluation.LOSS,
            "Loss function on the scored games",
            "The exact quantity this run minimized. It equals the log loss wherever a model is "
            "fitted with the plain one, and differs only where a model brought its own.",
            MetricUnit.SCORE,
            higher_is_better=False
        )
    )
}

ORDERED_ANSWER_METRICS = (
    evaluation.EXPECTED_VALUE_MAE,
    evaluation.EXPECTED_VALUE_MEDIAN_ERROR,
    evaluation.CENTRAL_INTERVAL_CALIBRATION_ERROR,
    evaluation.LINE_RANKED_PROBABILITY_SCORE,
    evaluation.ACCURACY,
    evaluation.CALIBRATION_ERROR
)
"""Default metrics for integer distribution models, most important first."""

CATEGORY_ANSWER_METRICS = (
    evaluation.ACCURACY,
    evaluation.PROBABILITY_OF_ACTUAL,
    evaluation.BRIER_SCORE,
    evaluation.CALIBRATION_ERROR
)
"""Default metrics for category models, most important first."""

def default_published_metrics(output: ModelOutput) -> tuple[str, ...]:
    """Returns the default metrics for the given output type."""

    if isinstance(output, IntegerDistribution):
        return ORDERED_ANSWER_METRICS

    if isinstance(output, CategoryDistribution):
        return CATEGORY_ANSWER_METRICS

    return ()

TEST_SPLIT_LABEL = "test"
"""Label for metrics computed on the test split."""

@dataclass(frozen=True)
class ModelEvaluation():
    """A model's evaluation results, as saved to disk."""

    model: str
    scored_on: str
    """The split the metrics were computed on."""

    samples: int
    first_game: str
    last_game: str
    """first_game and last_game are the date range of the evaluated games."""

    evaluated: str
    """When the model was evaluated."""

    metrics: dict[str, float]
    floor: dict[str, float] = field(default_factory=dict)
    """The same metrics for the baseline prediction."""

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2, sort_keys=True) + "\n"

def write(file_path: Path, model_evaluation: ModelEvaluation) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(model_evaluation.to_json(), encoding="utf-8")

    return file_path

def read(file_path: Path) -> ModelEvaluation | None:
    """Returns the saved evaluation, or None if the file is missing or invalid."""

    try:
        held = json.loads(file_path.read_text(encoding="utf-8"))

        return ModelEvaluation(**held)
    except (OSError, TypeError, ValueError):
        return None

def dates_covered(game_dates: np.ndarray | None) -> tuple[str, str]:
    """Returns the first and last game date as strings, or empty strings if there are no games."""

    if game_dates is None or len(game_dates) == 0:
        return ("", "")

    days = game_dates.astype("datetime64[D]")

    return (str(days.min()), str(days.max()))

def label_of(key: str) -> str:
    """Returns the metric's label, or its key with spaces if it has no definition."""

    described = ALL_METRICS.get(key)

    return described.label if described is not None else key.replace("_", " ")
