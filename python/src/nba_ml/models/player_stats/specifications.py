"""
The player game statistics models: what each one predicts, how it is shaped, and how it is fit.

Both training and inference read this, so it holds nothing that only one of them needs. Adding a
model means adding a ModelSpecification here and, for a new stat, a TargetStat in features.py.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import torch.nn as nn

from nba_ml import paths
from nba_ml.machine_learning import trainer
from nba_ml.machine_learning.architectures.feed_forward import LayerParameters
from nba_ml.machine_learning.losses.gaussian_smoothed_cross_entropy import GaussianSmoothedCrossEntropyLoss
from nba_ml.models.player_stats.features import FeatureSet, TargetStat, build_feature_set

MODEL_CATEGORY = "player_stats"
"""Names the folder every model of this family is saved under."""

SEQUENCE_SCALER = 'sequence_scaler'
STATIC_SCALER = 'static_scaler'

DEVICE = trainer.get_best_device()

# How many of the most recent games the GRU reads per prediction, or None for a player's entire history.
MAX_SEQUENCE_LENGTH: int | None = 50

GRU_HIDDEN_DIM = 64
GRU_LAYERS = 1
GRU_DROPOUT_RATE = 0.0

LossFunctionFactory = Callable[[int], trainer.LossFunction]
"""Builds a loss function once the number of classes is known."""

def cross_entropy_loss(num_classifications: int) -> trainer.LossFunction:
    return nn.CrossEntropyLoss()

def gaussian_smoothed_cross_entropy_loss(sigma: float) -> LossFunctionFactory:
    """
    Spreads each label over its neighbouring classes, so guessing 21 points when 20 happened costs
    less than guessing 40.

    Args:
        sigma is how far the label spreads, measured in classes.
    """

    return lambda num_classifications: GaussianSmoothedCrossEntropyLoss(num_classifications, sigma)

@dataclass(frozen=True)
class TrainingParameters():
    """Everything that decides how a model is fit, grouped so a run can be logged and repeated."""

    configuration: trainer.TrainingConfiguration
    hidden_layers: list[LayerParameters]
    learning_rate: float
    weight_decay: float = 0.01
    build_loss_function: LossFunctionFactory = cross_entropy_loss

DEFAULT_TRAINING_PARAMETERS = TrainingParameters(
    configuration=trainer.TrainingConfiguration(
        epochs=20,
        batch_size=128,
        patience=8,
        min_delta=0,
        max_gradient_norm=1.0,
        device=DEVICE
    ),
    hidden_layers=[
        LayerParameters(256, nn.ReLU(), False, 0.20),
        LayerParameters(128, nn.ReLU(), False, 0.15),
    ],
    learning_rate=0.00001
)

@dataclass(frozen=True)
class ModelSpecification():
    """
    One trained model: the name it is saved under, what it predicts, and how it is fit.

    The name is what `nba-train --model` and `nba-predict --model` take, so two models predicting the
    same stat with different settings are two specifications with different names.
    """

    name: str
    target_stats: tuple[TargetStat, ...]
    minimum_of_stat: int
    """The outcome the first predicted probability stands for."""

    number_of_stat_classifications: int
    training_parameters: TrainingParameters = DEFAULT_TRAINING_PARAMETERS
    """Set this to train with parameters other than the shared defaults."""

    def get_feature_set(self) -> FeatureSet:
        """
        Resolves which columns this model reads. Resolve it once per run and pass it down, so that
        two models being built at the same time never share column state.
        """

        return build_feature_set(self.target_stats)

    def model_file(self) -> Path:
        return paths.model_file(MODEL_CATEGORY, self.name)

    def training_report_file(self) -> Path:
        return paths.training_report_file(MODEL_CATEGORY, self.name)

    def training_cache_file(self) -> Path:
        return paths.training_cache_file(MODEL_CATEGORY, self.name)

    def graphs_directory(self) -> Path:
        return paths.graphs_directory(MODEL_CATEGORY, self.name)

POINTS_MODEL = ModelSpecification(
    "points",
    (TargetStat.POINTS,),
    0,
    60
    )

REBOUNDS_MODEL = ModelSpecification(
    "rebounds",
    (TargetStat.REBOUNDS,),
    0,
    25
    )

ASSISTS_MODEL = ModelSpecification(
    "assists",
    (TargetStat.ASSISTS,),
    0,
    20
    )

POINTS_REBOUNDS_ASSISTS_MODEL = ModelSpecification(
    "points_rebounds_assists",
    (TargetStat.POINTS, TargetStat.REBOUNDS, TargetStat.ASSISTS),
    0,
    80
    )

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        POINTS_MODEL,
        REBOUNDS_MODEL,
        ASSISTS_MODEL,
        POINTS_REBOUNDS_ASSISTS_MODEL
    )
}

MODEL_NAMES = sorted(ALL_MODEL_SPECIFICATIONS)
"""What `--model` accepts, so a command can list its choices without rebuilding them."""
