"""Specification and training parameters for classifier models."""

from dataclasses import dataclass, field
from typing import Callable

import torch.nn as nn

from nba_ml.machine_learning import trainer
from nba_ml.machine_learning.architectures.feed_forward import LayerParameters
from nba_ml.machine_learning.losses.gaussian_smoothed_cross_entropy import GaussianSmoothedCrossEntropyLoss
from nba_ml.models.outputs import ClassDistribution
from nba_ml.models.specifications import ModelSpecification

DEVICE = trainer.get_best_device()

LossFunctionFactory = Callable[[int], trainer.LossFunction]
"""Builds a loss function given the number of classes."""

def cross_entropy_loss(num_classifications: int) -> trainer.LossFunction:
    return nn.CrossEntropyLoss()

def gaussian_smoothed_cross_entropy_loss(sigma: float) -> LossFunctionFactory:
    """Returns a loss factory that smooths labels over neighbouring classes. Only for ordered outputs."""

    return lambda num_classifications: GaussianSmoothedCrossEntropyLoss(num_classifications, sigma)

@dataclass(frozen=True)
class TrainingParameters():
    """Hyperparameters for training a model."""

    configuration: trainer.TrainingConfiguration
    hidden_layers: list[LayerParameters]
    """Layers of the feed forward network that follows the GRU."""

    learning_rate: float
    weight_decay: float = 0.01
    build_loss_function: LossFunctionFactory = cross_entropy_loss

    gru_hidden_dim: int = 64
    """Size of the GRU's hidden state."""

    gru_layers: int = 1
    gru_dropout_rate: float = 0.0
    """Only applies between GRU layers, so it is ignored when gru_layers is 1."""

DEFAULT_TRAINING_PARAMETERS = TrainingParameters(
    configuration=trainer.TrainingConfiguration(
        epochs=20,
        batch_size=128,
        patience=7,
        min_delta=0,
        max_gradient_norm=1.0,
        device=DEVICE
    ),
    hidden_layers=[
        LayerParameters(256, nn.ReLU(), False, 0.20),
        LayerParameters(128, nn.ReLU(), False, 0.15),
    ],
    learning_rate=0.00002
)
"""Default parameters for families that don't define their own."""

@dataclass(frozen=True)
class ClassifierModelSpecification(ModelSpecification):
    """Base specification for classifier models. Each family subclasses it and adds its own fields."""

    output: ClassDistribution

    training_parameters: TrainingParameters = field(default=DEFAULT_TRAINING_PARAMETERS, kw_only=True)
    """Override this to train with non-default parameters."""
