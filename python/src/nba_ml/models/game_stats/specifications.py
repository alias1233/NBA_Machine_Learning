"""
What each game statistics model is, and how it is fit.

Neither model names a team. A point differential still has a direction, so it is read off the home
team's row and a positive answer is the home team's margin. A game total is the same number from
either side.

A game is one sample rather than two, so this family has about 51,000 of them, half what team
statistics has and fourteen times fewer than a player model. Every model here therefore answers in
buckets of whole numbers rather than in single ones, because a class per outcome would be fit on a
few hundred games and answer with noise.
"""

from dataclasses import dataclass, field
from typing import ClassVar

import torch.nn as nn

from nba_ml.machine_learning import trainer
from nba_ml.machine_learning.architectures.feed_forward import LayerParameters
from nba_ml.models.classifiers import DEVICE, ClassifierModelSpecification, TrainingParameters
from nba_ml.models.game_stats import features
from nba_ml.models.game_stats.features import FeatureSet, TargetValue
from nba_ml.models.outputs import IntegerDistribution

MODEL_CATEGORY = "game_stats"
"""Names the folder every model of this family is saved under."""

# How many of the most recent games the network reads per history, or None for a whole one. Around
# half a season, which is as far back as a roster still resembles the one playing.
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
"""
Where this family is fit, each part measured against the alternatives on 2026-08-11.

Fewer samples did not want a faster learning rate, as it might sound: every rate above this one was
worse, and the fastest tried was 1.2% worse. Nor did they want more memory of past games. Widening
the network either side of these numbers cost accuracy, which is what a family with 51,000 samples
should be expected to do. See docs/STATUS.md for the figures.
"""

@dataclass(frozen=True)
class GameStatModelSpecification(ClassifierModelSpecification):
    """One game statistics model. Asking for one names the game and nothing else."""

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

    training_parameters: TrainingParameters = field(default=GAME_STAT_TRAINING_PARAMETERS, kw_only=True)

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

POINT_DIFFERENTIAL_MODEL = GameStatModelSpecification(
    name="point_differential",
    # -42 to 41, in threes. Zero starts a bucket, so no bucket ever mixes a home win with a home
    # loss and the chance the home team wins stays an exact sum rather than a share of one bucket.
    output=IntegerDistribution(minimum_value=-42, outcomes=28, bucket_width=3),
    target=TargetValue.POINT_DIFFERENTIAL,
    predicted="point differential"
    )
"""
How much the home team wins or loses by. Everything from zero up is the home team winning.

A game cannot end level, so the bucket starting at zero is really a home win by one or two.
"""

GAME_TOTAL_MODEL = GameStatModelSpecification(
    name="game_total",
    # 171 to 275, in threes. Wider than the other two because a total is two scores added, so it
    # spreads about half as much again. Each end folds in about 1%, against 2.8% in the middle.
    output=IntegerDistribution(minimum_value=171, outcomes=35, bucket_width=3),
    target=TargetValue.GAME_TOTAL,
    predicted="game total"
    )
"""How many points both teams score together."""

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        POINT_DIFFERENTIAL_MODEL,
        GAME_TOTAL_MODEL
    )
}
