"""
What each game statistics model is, and how it is fit.

No model here names a team. An answer with a direction is read off the home team's row, so a positive
point differential is the home team's margin and the first win category is the home team's. A game
total is the same number from either side. A model whose answer belongs to a side says which one, so
a caller holding the game can name the team rather than say home.

A game is one sample rather than two, so this family has about 51,000 of them, half what team
statistics has and fourteen times fewer than a player model. A model here answering with a number
therefore answers in buckets of whole numbers rather than in single ones, because a class per outcome
would be fit on a few hundred games and answer with noise.
"""

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
"""Names the folder every model of this family is saved under."""

DRAWN_GAME = 0
"""
The point differential a basketball game cannot end on, because it is played until somebody leads.

Naming it takes it off the number line rather than out of one bucket, so the buckets either side of
it are as wide as every other one. Nothing claims an outcome that never happens: no bucket covers it,
no label mentions it, and the odds on a line never spread onto it.
"""

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
    """
    One game statistics model. Asking for one names the game and nothing else.

    An answer is a chance per bucket of whole numbers, or a chance per named category where the
    outcome sits on no number line, such as which side wins.

    A whole number range is chosen so the class at each end folds in a tail no bigger than a class in
    the body carries. Every value below the range counts as the first class and every value above it
    as the last, so the ends are real outcomes rather than a cut in the data.
    """

    model_category: ClassVar[str] = MODEL_CATEGORY

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
    # -42 to 42 without zero, in threes: -3 to -1, then 1 to 3. Zero falls on a bucket edge, so no
    # bucket mixes a home win with a home loss and the range is the same reach either side.
    output=IntegerDistribution(
        minimum_value=-42, outcomes=28, bucket_width=3, impossible_value=DRAWN_GAME
    ),
    target=TargetValue.POINT_DIFFERENTIAL,
    predicted="point differential",
    read_from=GameSide.HOME
    )
"""
How much the home team wins or loses by. Everything above zero is the home team winning.

A basketball game cannot end level, so zero is named as the one outcome that cannot happen and comes
off the line entirely. The first bucket above it is a home win by one, two or three.
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

WIN_CATEGORIES = ("home win", "away win")
"""
What the win probability model answers with, in the order team_game_rows.WON and LOST number them.

A sample is read off the home team's row, so its win is the first category, which is the one a reader
is led with. A basketball game cannot end level, so the second is the away team winning rather than
the home team not winning.

Each name leads with the side it belongs to, which is what lets a caller holding the game put the
team playing that side in place of the word.
"""

WIN_CATEGORY_SIDES = (GameSide.HOME, GameSide.AWAY)
"""Which side each win category names, read beside WIN_CATEGORIES by position."""

WIN_PROBABILITY_MODEL = GameStatModelSpecification(
    name="win_probability",
    output=CategoryDistribution(categories=WIN_CATEGORIES),
    target=TargetValue.RESULT,
    predicted="win chances",
    category_sides=WIN_CATEGORY_SIDES
    )
"""
The chance the home team wins.

It reads exactly what the point differential model reads and is fit the same way, and the two answer
the same question. This is the better answer of the two: adding up the positive half of a
differential is a worse reading than a model fit to give the figure outright.
"""

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        POINT_DIFFERENTIAL_MODEL,
        GAME_TOTAL_MODEL,
        WIN_PROBABILITY_MODEL
    )
}
