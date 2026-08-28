"""
What a scored model recorded, and how a reader is told about it.

A training run writes one of these files beside the model it fitted. The service reads it back and
puts it on the family Info page, so a visitor sees measured figures rather than claims. The file is
plain JSON, so nothing has to load PyTorch to read it and publishing a model still copies files.

Two things are deliberately kept apart. The **file** holds only identifiers and numbers, which is
what a run can honestly record. The **wording** is in the catalogue below, so rewriting how a figure
is explained is a code change rather than a retraining run.

Which figures a model publishes is the model's own choice. Accuracy says nothing about a triple
double, because always answering no scores 99.5%, and an average miss says nothing about a yes or no
answer at all. A model names the figures worth reading and nothing else reaches the site.
"""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import numpy as np

from nba_ml.machine_learning import evaluation
from nba_ml.models.outputs import CategoryDistribution, IntegerDistribution, ModelOutput

class MetricUnit(StrEnum):
    """What a figure is measured in, which is all a caller needs to write it down."""

    VALUE = "value"
    """In the statistic's own units, such as points. What the model predicts names them."""

    PROBABILITY = "probability"
    """Between zero and one, read as a percentage."""

    SCORE = "score"
    """A number with no units, meaningful only against the floor beside it."""

@dataclass(frozen=True)
class Metric():
    """One figure a model can be scored on, in the words a reader sees."""

    key: str
    """How the figure is named in a saved evaluation file. See machine_learning/evaluation.py."""

    label: str
    description: str
    """One sentence saying what the figure means, written for somebody who has not read the code."""

    unit: MetricUnit
    higher_is_better: bool
    ideal: float | None = None
    """The value this figure should reach, when closer is better than simply higher or lower."""

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
"""
What a model answering over a run of whole numbers publishes, headline first.

The average miss leads, because it is the only one of these a reader needs nothing explained to
understand. Exact answers come late on purpose: a model over sixty outcomes is right outright about
one game in seven and that reads as a failure until the average miss beside it says otherwise.
"""

CATEGORY_ANSWER_METRICS = (
    evaluation.ACCURACY,
    evaluation.PROBABILITY_OF_ACTUAL,
    evaluation.BRIER_SCORE,
    evaluation.CALIBRATION_ERROR
)
"""What a model answering with named categories publishes, headline first."""

def default_published_metrics(output: ModelOutput) -> tuple[str, ...]:
    """
    The figures worth showing for an answer of this shape, which a model may replace with its own.

    A shape this does not know publishes nothing rather than a figure that does not apply to it, so
    adding an answer shape cannot put a meaningless number on the site.
    """

    if isinstance(output, IntegerDistribution):
        return ORDERED_ANSWER_METRICS

    if isinstance(output, CategoryDistribution):
        return CATEGORY_ANSWER_METRICS

    return ()

TEST_SPLIT_LABEL = "test"
"""Which split a figure was scored on. Only a held-out one is worth publishing."""

@dataclass(frozen=True)
class ModelEvaluation():
    """
    One model's finished score, as it is written to disk.

    Everything here is what the run measured. Nothing here is wording, so the site can be rewritten
    without a model being fitted again.
    """

    model: str
    scored_on: str
    """Which split produced these figures. See TEST_SPLIT_LABEL."""

    samples: int
    first_game: str
    last_game: str
    """The stretch of calendar the scored games cover, written as dates."""

    evaluated: str
    """When the run scored the model, so a stale figure can be spotted."""

    metrics: dict[str, float]
    floor: dict[str, float] = field(default_factory=dict)
    """
    The same figures scored on an answer that reads nothing.

    It is the season's own spread of outcomes, repeated for every game. A model has to beat this to
    be worth having, so it is what turns a figure into a claim a reader can check.
    """

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2, sort_keys=True) + "\n"

def write(file_path: Path, model_evaluation: ModelEvaluation) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(model_evaluation.to_json(), encoding="utf-8")

    return file_path

def read(file_path: Path) -> ModelEvaluation | None:
    """
    What a run recorded for one model, or None where there is nothing readable.

    A missing or unreadable file is not an error. A model can be published before it is scored, and
    a file written by older code may hold fields this no longer expects, so a caller is told there
    is no score rather than handed a broken one.
    """

    try:
        held = json.loads(file_path.read_text(encoding="utf-8"))

        return ModelEvaluation(**held)
    except (OSError, TypeError, ValueError):
        return None

def dates_covered(game_dates: np.ndarray | None) -> tuple[str, str]:
    """
    The first and last day a set of scored games covers, written as plain dates.

    Both splits now span the same stretch of calendar, so this is what proves it rather than a claim
    that they do.
    """

    if game_dates is None or len(game_dates) == 0:
        return ("", "")

    days = game_dates.astype("datetime64[D]")

    return (str(days.min()), str(days.max()))

def label_of(key: str) -> str:
    """What a figure is called, falling back to its own name where nothing describes it."""

    described = ALL_METRICS.get(key)

    return described.label if described is not None else key.replace("_", " ")
