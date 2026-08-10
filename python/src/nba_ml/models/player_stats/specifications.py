"""
The player game statistics models: what each one predicts, how it is shaped, and how it is fit.

Both training and inference read this, so it holds nothing that only one of them needs. Adding a
model means adding a PlayerStatModelSpecification here and, for a new stat, a TargetStat in
features.py.
"""

from dataclasses import dataclass
from typing import Callable, ClassVar

import torch.nn as nn

from nba_ml.machine_learning import trainer
from nba_ml.models.outputs import CategoryDistribution, ClassDistribution, IntegerDistribution
from nba_ml.models.specifications import ModelSpecification
from nba_ml.machine_learning.architectures.feed_forward import LayerParameters
from nba_ml.machine_learning.losses.gaussian_smoothed_cross_entropy import GaussianSmoothedCrossEntropyLoss
from nba_ml.models.player_stats.features import (
    MILESTONE_CATEGORIES,
    DoubleFigureMilestone,
    FeatureSet,
    StatCombination,
    StatTotal,
    TargetStat,
    build_feature_set
)

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
    learning_rate: float
    weight_decay: float = 0.01
    build_loss_function: LossFunctionFactory = cross_entropy_loss

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

@dataclass(frozen=True)
class PlayerStatModelSpecification(ModelSpecification):
    """One player game statistics model: which stats it reads, how they combine, and how it is fit."""

    model_category: ClassVar[str] = MODEL_CATEGORY

    output: ClassDistribution
    """Narrowed, because every model here is fit as a classifier over the positions its output lists."""

    target_stats: tuple[TargetStat, ...]
    combination: StatCombination = StatTotal()
    """How those stats become the one value the model is fit against."""

    training_parameters: TrainingParameters = DEFAULT_TRAINING_PARAMETERS
    """Set this to train with parameters other than the shared defaults."""

    @property
    def predicts(self) -> tuple[str, ...]:
        return self.combination.predicts(self.target_stats)

    def get_feature_set(self) -> FeatureSet:
        """
        Resolves which columns this model reads. Resolve it once per run and pass it down, so that
        two models being built at the same time never share column state.
        """

        return build_feature_set(self.target_stats, self.combination)

# Every whole number range below leaves out under 0.02% of the 838,852 collected player games, which
# is the room a distribution needs at its tails.
POINTS_MODEL = PlayerStatModelSpecification(
    name="points",
    output=IntegerDistribution(minimum_value=0, outcomes=60),
    target_stats=(TargetStat.POINTS,)
    )

REBOUNDS_MODEL = PlayerStatModelSpecification(
    name="rebounds",
    output=IntegerDistribution(minimum_value=0, outcomes=25),
    target_stats=(TargetStat.REBOUNDS,)
    )

ASSISTS_MODEL = PlayerStatModelSpecification(
    name="assists",
    output=IntegerDistribution(minimum_value=0, outcomes=20),
    target_stats=(TargetStat.ASSISTS,)
    )

THREE_POINTERS_MODEL = PlayerStatModelSpecification(
    name="three_pointers",
    output=IntegerDistribution(minimum_value=0, outcomes=12),
    target_stats=(TargetStat.THREE_POINTERS,)
    )

STEALS_MODEL = PlayerStatModelSpecification(
    name="steals",
    output=IntegerDistribution(minimum_value=0, outcomes=10),
    target_stats=(TargetStat.STEALS,)
    )

BLOCKS_MODEL = PlayerStatModelSpecification(
    name="blocks",
    output=IntegerDistribution(minimum_value=0, outcomes=10),
    target_stats=(TargetStat.BLOCKS,)
    )

TURNOVERS_MODEL = PlayerStatModelSpecification(
    name="turnovers",
    output=IntegerDistribution(minimum_value=0, outcomes=12),
    target_stats=(TargetStat.TURNOVERS,)
    )

POINTS_REBOUNDS_MODEL = PlayerStatModelSpecification(
    name="points_rebounds",
    output=IntegerDistribution(minimum_value=0, outcomes=70),
    target_stats=(TargetStat.POINTS, TargetStat.REBOUNDS)
    )

POINTS_ASSISTS_MODEL = PlayerStatModelSpecification(
    name="points_assists",
    output=IntegerDistribution(minimum_value=0, outcomes=70),
    target_stats=(TargetStat.POINTS, TargetStat.ASSISTS)
    )

REBOUNDS_ASSISTS_MODEL = PlayerStatModelSpecification(
    name="rebounds_assists",
    output=IntegerDistribution(minimum_value=0, outcomes=35),
    target_stats=(TargetStat.REBOUNDS, TargetStat.ASSISTS)
    )

STEALS_BLOCKS_MODEL = PlayerStatModelSpecification(
    name="steals_blocks",
    output=IntegerDistribution(minimum_value=0, outcomes=12),
    target_stats=(TargetStat.STEALS, TargetStat.BLOCKS)
    )

POINTS_REBOUNDS_ASSISTS_MODEL = PlayerStatModelSpecification(
    name="points_rebounds_assists",
    output=IntegerDistribution(minimum_value=0, outcomes=80),
    target_stats=(TargetStat.POINTS, TargetStat.REBOUNDS, TargetStat.ASSISTS)
    )

MILESTONE_STATS = (
    TargetStat.POINTS,
    TargetStat.REBOUNDS,
    TargetStat.ASSISTS,
    TargetStat.STEALS,
    TargetStat.BLOCKS
)
"""The five stats a double double and a triple double are counted over."""

MILESTONE_OUTPUT = CategoryDistribution(categories=MILESTONE_CATEGORIES)

DOUBLE_DOUBLE_MODEL = PlayerStatModelSpecification(
    name="double_double",
    output=MILESTONE_OUTPUT,
    target_stats=MILESTONE_STATS,
    combination=DoubleFigureMilestone(stats_needed=2, predicted="double double")
    )

TRIPLE_DOUBLE_MODEL = PlayerStatModelSpecification(
    name="triple_double",
    output=MILESTONE_OUTPUT,
    target_stats=MILESTONE_STATS,
    combination=DoubleFigureMilestone(stats_needed=3, predicted="triple double")
    )

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        POINTS_MODEL,
        REBOUNDS_MODEL,
        ASSISTS_MODEL,
        THREE_POINTERS_MODEL,
        STEALS_MODEL,
        BLOCKS_MODEL,
        TURNOVERS_MODEL,
        POINTS_REBOUNDS_MODEL,
        POINTS_ASSISTS_MODEL,
        REBOUNDS_ASSISTS_MODEL,
        STEALS_BLOCKS_MODEL,
        POINTS_REBOUNDS_ASSISTS_MODEL,
        DOUBLE_DOUBLE_MODEL,
        TRIPLE_DOUBLE_MODEL
    )
}

MODEL_NAMES = sorted(ALL_MODEL_SPECIFICATIONS)
"""What `--model` accepts, so a command can list its choices without rebuilding them."""
