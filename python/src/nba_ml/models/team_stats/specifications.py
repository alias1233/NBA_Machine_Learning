"""Defines the team stats models and their training parameters."""

from dataclasses import dataclass, field
from typing import ClassVar

import torch.nn as nn

from nba_ml.machine_learning import trainer
from nba_ml.machine_learning.architectures.feed_forward import LayerParameters
from nba_ml.models.classifiers import DEVICE, ClassifierModelSpecification, TrainingParameters
from nba_ml.models.outputs import IntegerDistribution
from nba_ml.models.team_stats import features
from nba_ml.models.team_stats.features import FeatureSet, TargetValue

MODEL_CATEGORY = "team_stats"
"""Name of the folder this family's models are saved in."""

# Number of most recent games the model uses per sequence, or None for all of them.
MAX_SEQUENCE_LENGTH: int | None = 50

TEAM_STAT_TRAINING_PARAMETERS = TrainingParameters(
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
class TeamStatModelSpecification(ClassifierModelSpecification):
    """Specification for a team stats model."""

    model_category: ClassVar[str] = MODEL_CATEGORY

    output: IntegerDistribution
    """Every team stats model outputs an integer distribution."""

    target: TargetValue
    """The value this model predicts."""

    predicted: str
    """Display name of the predicted value."""

    training_parameters: TrainingParameters = field(default=TEAM_STAT_TRAINING_PARAMETERS, kw_only=True)

    @property
    def predicts(self) -> tuple[str, ...]:
        return (self.predicted,)

    @property
    def sequences_read(self) -> int:
        return features.SEQUENCES_READ

    def get_feature_set(self) -> FeatureSet:
        """Returns the feature set for this model."""

        return features.build_feature_set(self.target)

TEAM_POINTS_MODEL = TeamStatModelSpecification(
    name="team_points",
    title="Team points",
    description="How many points one team scores in a game.",
    # 80 to 145 in buckets of 3.
    output=IntegerDistribution(minimum_value=80, outcomes=22, bucket_width=3),
    target=TargetValue.TEAM_POINTS,
    predicted="team points"
    )

TEAM_REBOUNDS_MODEL = TeamStatModelSpecification(
    name="team_rebounds",
    title="Team rebounds",
    description="How many rebounds one team takes in a game.",
    # 30 to 61 in buckets of 2.
    output=IntegerDistribution(minimum_value=30, outcomes=16, bucket_width=2),
    target=TargetValue.TEAM_REBOUNDS,
    predicted="team rebounds"
    )

TEAM_ASSISTS_MODEL = TeamStatModelSpecification(
    name="team_assists",
    title="Team assists",
    description="How many assists one team records in a game.",
    # 13 to 37, one class per assist.
    output=IntegerDistribution(minimum_value=13, outcomes=25),
    target=TargetValue.TEAM_ASSISTS,
    predicted="team assists"
    )

TEAM_THREE_POINTERS_MODEL = TeamStatModelSpecification(
    name="team_three_pointers",
    title="Team three-pointers",
    description="How many three-pointers one team makes in a game.",
    # 4 to 22, one class per make.
    output=IntegerDistribution(minimum_value=4, outcomes=19),
    target=TargetValue.TEAM_THREE_POINTERS,
    predicted="team three-pointers"
    )

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        TEAM_POINTS_MODEL,
        TEAM_REBOUNDS_MODEL,
        TEAM_ASSISTS_MODEL,
        TEAM_THREE_POINTERS_MODEL
    )
}
