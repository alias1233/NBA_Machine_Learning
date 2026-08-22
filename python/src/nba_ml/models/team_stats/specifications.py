"""
What each team statistics model is, and how it is fit.

A team statistic is asked about one named team in one game, so a sample is one side of a game and
both sides are samples. That gives this family about 102,000 samples, which is seven times fewer
than the player models have, and twice what game statistics has.

Fewer samples than a player model is why the network below is smaller, and why the answer is a
probability per bucket of points rather than per single point. Buckets of three were measured better
than a class per point on 2026-08-11, by about two thirds of a percent, which is a smaller margin
than game statistics saw and in the same direction.
"""

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
"""Names the folder every model of this family is saved under."""

# How many of the most recent games the network reads per history, or None for a whole one. Around
# half a season, which is as far back as a roster still resembles the one playing.
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
"""
Where this family is fit, measured against the alternatives on 2026-08-11.

Seven times fewer samples than a player model, so the fully connected half is half the width the
player models carry. Every learning rate faster than this one read worse, which is the opposite of
what fewer weight updates per epoch might suggest. Nothing here wants more capacity: a wider memory
of past games was measured worse on the game statistics models, which read the same rows.
The figures are in the training reports the runs wrote.
"""

@dataclass(frozen=True)
class TeamStatModelSpecification(ClassifierModelSpecification):
    """One team statistics model. Asking for one names the team it is about."""

    model_category: ClassVar[str] = MODEL_CATEGORY

    output: IntegerDistribution
    """
    Narrowed: every model here answers over a run of whole numbers, in buckets of bucket_width.

    A range is chosen so the class at each end folds in a tail no bigger than a class in the body
    carries. Every value below the range counts as the first class and every value above it as the
    last, so the ends are real outcomes rather than a cut in the data.
    """

    target: TargetValue
    """Which finished column of the build the value being predicted is read off."""

    predicted: str
    """What a reader calls it."""

    training_parameters: TrainingParameters = field(default=TEAM_STAT_TRAINING_PARAMETERS, kw_only=True)

    @property
    def predicts(self) -> tuple[str, ...]:
        return (self.predicted,)

    @property
    def sequences_read(self) -> int:
        return features.SEQUENCES_READ

    def get_feature_set(self) -> FeatureSet:
        """
        Resolves which columns this model reads. Resolve it once per run and pass it down, so that
        two models being built at the same time never share column state.
        """

        return features.build_feature_set(self.target)

TEAM_POINTS_MODEL = TeamStatModelSpecification(
    name="team_points",
    title="Team points",
    description="How many points one team scores in a game.",
    # 80 to 145, in threes. Measured against every game since 2015, which is the scoring the site is
    # asked about. Each end folds in under 1.5%, against 4.1% in the class the middle carries.
    output=IntegerDistribution(minimum_value=80, outcomes=22, bucket_width=3),
    target=TargetValue.TEAM_POINTS,
    predicted="team points"
    )
"""How many points one team scores."""

# Every range below is picked the way team points was: each end class folds in about 1% of the games
# played since 2015, and the bucket width is chosen so a class in the middle carries about as much
# data as one of that model's does. That figure is what bucket_width exists to control, and buckets
# of three were measured better than a class per whole number here on 2026-08-11 for exactly that
# reason. Rebounds are narrow enough to want twos, and assists and three-pointers narrower still, so
# a class per whole number already leaves each one as much data as a team points class has.
TEAM_REBOUNDS_MODEL = TeamStatModelSpecification(
    name="team_rebounds",
    title="Team rebounds",
    description="How many rebounds one team takes in a game.",
    # 30 to 61, in twos. Folds 1.0% below and 0.7% above, against 12.0% in the middle class.
    output=IntegerDistribution(minimum_value=30, outcomes=16, bucket_width=2),
    target=TargetValue.TEAM_REBOUNDS,
    predicted="team rebounds"
    )
"""How many rebounds one team takes, offensive and defensive together."""

TEAM_ASSISTS_MODEL = TeamStatModelSpecification(
    name="team_assists",
    title="Team assists",
    description="How many assists one team records in a game.",
    # 13 to 37, one class per assist. Folds 0.8% below and 1.1% above, against 7.9% in the middle.
    output=IntegerDistribution(minimum_value=13, outcomes=25),
    target=TargetValue.TEAM_ASSISTS,
    predicted="team assists"
    )
"""How many assists one team records."""

TEAM_THREE_POINTERS_MODEL = TeamStatModelSpecification(
    name="team_three_pointers",
    title="Team three-pointers",
    description="How many three-pointers one team makes in a game.",
    # 4 to 22, one class per make. Folds 1.0% below and 0.8% above, against 9.7% in the middle.
    output=IntegerDistribution(minimum_value=4, outcomes=19),
    target=TargetValue.TEAM_THREE_POINTERS,
    predicted="team three-pointers"
    )
"""How many three-pointers one team makes."""

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        TEAM_POINTS_MODEL,
        TEAM_REBOUNDS_MODEL,
        TEAM_ASSISTS_MODEL,
        TEAM_THREE_POINTERS_MODEL
    )
}
