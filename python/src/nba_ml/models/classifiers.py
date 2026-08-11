"""
A model fit as a classifier: a probability for each position of its output.

Both families here answer with a probability per class, whether those positions are whole numbers or
named categories, so one training run fits either. What such a run needs beyond the shared
specification sits here: the answer shape narrowed to a classification, and every knob that decides
how the fit goes.

A family that answers with something else, such as a plain amount, subclasses ModelSpecification
directly and brings its own trainer. Nothing here is imposed on it.
"""

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
"""Builds a loss function once the number of classes is known."""

def cross_entropy_loss(num_classifications: int) -> trainer.LossFunction:
    return nn.CrossEntropyLoss()

def gaussian_smoothed_cross_entropy_loss(sigma: float) -> LossFunctionFactory:
    """
    Spreads each label over its neighbouring classes, so guessing 21 points when 20 happened costs
    less than guessing 40. Only for a model whose output is ordered, since an unordered category has
    no neighbours to spread onto.

    Args:
        sigma is how far the label spreads, measured in classes.
    """

    return lambda num_classifications: GaussianSmoothedCrossEntropyLoss(num_classifications, sigma)

@dataclass(frozen=True)
class TrainingParameters():
    """Everything that decides how a model is fit, grouped so a run can be logged and repeated."""

    configuration: trainer.TrainingConfiguration
    hidden_layers: list[LayerParameters]
    """The fully connected half, which reads the sequence memory beside the predicted game."""

    learning_rate: float
    weight_decay: float = 0.01
    build_loss_function: LossFunctionFactory = cross_entropy_loss

    gru_hidden_dim: int = 64
    """How much the network remembers of the past games it reads."""

    gru_layers: int = 1
    gru_dropout_rate: float = 0.0
    """Only applies between GRU layers, so it is ignored while gru_layers is 1."""

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
"""
The starting point a family inherits without saying anything.

Swept on 2026-08-04 against a sixty class player points model with 750,000 samples, so a family
whose data is a different size or shape should measure its own rather than assume these.
"""

@dataclass(frozen=True)
class ClassifierModelSpecification(ModelSpecification):
    """One model fit as a classifier. A family subclasses this and adds what only it reads."""

    output: ClassDistribution
    """Narrowed, because a classifier is fit over the positions its output lists."""

    training_parameters: TrainingParameters = field(default=DEFAULT_TRAINING_PARAMETERS, kw_only=True)
    """
    Set this to fit with parameters other than the inherited defaults.

    Keyword only, so a family can add its own required fields after it without every model having to
    name this one.
    """
