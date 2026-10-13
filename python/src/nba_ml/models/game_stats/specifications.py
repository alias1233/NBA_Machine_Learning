"""Defines the game stats models and their training parameters."""

from dataclasses import dataclass, field
from typing import ClassVar

import torch.nn as nn

from nba_ml.machine_learning import trainer
from nba_ml.machine_learning.architectures.feed_forward import LayerParameters
from nba_ml.models.classifiers import DEVICE, ClassifierModelSpecification, TrainingParameters
from nba_ml.models.game_stats import features
from nba_ml.models.game_stats.features import FeatureSet, TargetValue
from nba_ml.models.outputs import CategoryDistribution, IntegerDistribution
from nba_ml.models.specifications import GameSide

MODEL_CATEGORY = "game_stats"
"""Name of the folder this family's models are saved in."""

DRAWN_GAME = 0
"""A point differential of 0 is impossible, since NBA games can't end in a tie."""

# Number of most recent games the model uses per sequence, or None for all of them.
MAX_SEQUENCE_LENGTH: int | None = 50

GAME_STAT_TRAINING_PARAMETERS = TrainingParameters(
    configuration=trainer.TrainingConfiguration(
        epochs=40,
        batch_size=128,
        patience=8,
        min_delta=0,
        max_gradient_norm=1.0,
        device=DEVICE
    ),
    hidden_layers=[
        LayerParameters(128, nn.ReLU(), False, 0.20),
        LayerParameters(64, nn.ReLU(), False, 0.15),
    ],
    learning_rate=0.00003
)

@dataclass(frozen=True)
class GameStatModelSpecification(ClassifierModelSpecification):
    """Specification for a game stats model. A request only needs the game."""

    model_category: ClassVar[str] = MODEL_CATEGORY

    target: TargetValue
    """The value this model predicts."""

    predicted: str
    """Display name of the predicted value."""

    training_parameters: TrainingParameters = field(default=GAME_STAT_TRAINING_PARAMETERS, kw_only=True)

    @property
    def predicts(self) -> tuple[str, ...]:
        return (self.predicted,)

    @property
    def sequences_read(self) -> int:
        return features.SEQUENCES_READ

    def get_feature_set(self) -> FeatureSet:
        """Returns the feature set for this model."""

        return features.build_feature_set(self.target)

POINT_DIFFERENTIAL_MODEL = GameStatModelSpecification(
    name="point_differential",
    title="Point differential",
    description="The home team's margin, positive for a win and negative for a loss.",
    # -42 to 42 in buckets of 3, skipping 0. For example, -3 to -1, then 1 to 3.
    output=IntegerDistribution(
        minimum_value=-42, outcomes=28, bucket_width=3, impossible_value=DRAWN_GAME
    ),
    target=TargetValue.POINT_DIFFERENTIAL,
    predicted="point differential",
    read_from=GameSide.HOME
    )
"""Predicts the home team's margin. A positive value means the home team wins."""

TOTAL_POINTS = GameStatModelSpecification(
    name="total_points",
    title="Total points",
    description="The points both teams score together.",
    # 171 to 275 in buckets of 3.
    output=IntegerDistribution(minimum_value=171, outcomes=35, bucket_width=3),
    target=TargetValue.GAME_TOTAL,
    predicted="game total"
    )

WIN_CATEGORIES = ("home win", "away win")
"""Output categories of the win probability model. The home win comes first."""

WIN_CATEGORY_SIDES = (GameSide.HOME, GameSide.AWAY)
"""The team each entry in WIN_CATEGORIES refers to, in the same order."""

WIN_PROBABILITY_MODEL = GameStatModelSpecification(
    name="win_probability",
    title="Win probability",
    description="The chance of each team winning the game.",
    output=CategoryDistribution(categories=WIN_CATEGORIES),
    target=TargetValue.RESULT,
    predicted="win chances",
    category_sides=WIN_CATEGORY_SIDES
    )

TOTAL_REBOUNDS_MODEL = GameStatModelSpecification(
    name="total_rebounds",
    title="Total rebounds",
    description="The rebounds both teams take together.",
    # 68 to 110, one class per rebound.
    output=IntegerDistribution(minimum_value=68, outcomes=43),
    target=TargetValue.TOTAL_REBOUNDS,
    predicted="total rebounds"
    )

TOTAL_ASSISTS_MODEL = GameStatModelSpecification(
    name="total_assists",
    title="Total assists",
    description="The assists both teams record together.",
    # 31 to 68, one class per assist.
    output=IntegerDistribution(minimum_value=31, outcomes=38),
    target=TargetValue.TOTAL_ASSISTS,
    predicted="total assists"
    )

TOTAL_THREE_POINTERS_MODEL = GameStatModelSpecification(
    name="total_three_pointers",
    title="Total three-pointers",
    description="The three-pointers both teams make together.",
    # 10 to 38, one class per make.
    output=IntegerDistribution(minimum_value=10, outcomes=29),
    target=TargetValue.TOTAL_THREE_POINTERS,
    predicted="total three-pointers"
    )

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        POINT_DIFFERENTIAL_MODEL,
        TOTAL_POINTS,
        WIN_PROBABILITY_MODEL,
        TOTAL_REBOUNDS_MODEL,
        TOTAL_ASSISTS_MODEL,
        TOTAL_THREE_POINTERS_MODEL
    )
}
