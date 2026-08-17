"""
The player game statistics models: what each one predicts, how it is shaped, and how it is fit.

Both training and inference read this, so it holds nothing that only one of them needs. Adding a
model means adding a PlayerStatModelSpecification here and, for a new stat, a TargetStat in
features.py.
"""

from dataclasses import dataclass
from typing import ClassVar

from nba_ml.machine_learning import evaluation
from nba_ml.models.classifiers import ClassifierModelSpecification
from nba_ml.models.outputs import CategoryDistribution, IntegerDistribution
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

# How many of the most recent games the GRU reads per prediction, or None for a player's entire history.
MAX_SEQUENCE_LENGTH: int | None = 50

@dataclass(frozen=True)
class PlayerStatModelSpecification(ClassifierModelSpecification):
    """One player game statistics model: which stats it reads, how they combine, and how it is fit."""

    model_category: ClassVar[str] = MODEL_CATEGORY

    target_stats: tuple[TargetStat, ...]
    combination: StatCombination = StatTotal()
    """How those stats become the one value the model is fit against."""

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
    title="Points",
    description="How many points one player records in a game.",
    output=IntegerDistribution(minimum_value=0, outcomes=60),
    target_stats=(TargetStat.POINTS,)
    )

REBOUNDS_MODEL = PlayerStatModelSpecification(
    name="rebounds",
    title="Rebounds",
    description="How many rebounds one player records in a game.",
    output=IntegerDistribution(minimum_value=0, outcomes=25),
    target_stats=(TargetStat.REBOUNDS,)
    )

ASSISTS_MODEL = PlayerStatModelSpecification(
    name="assists",
    title="Assists",
    description="How many assists one player records in a game.",
    output=IntegerDistribution(minimum_value=0, outcomes=20),
    target_stats=(TargetStat.ASSISTS,)
    )

THREE_POINTERS_MODEL = PlayerStatModelSpecification(
    name="three_pointers",
    title="Three-pointers",
    description="How many three-pointers one player makes in a game.",
    output=IntegerDistribution(minimum_value=0, outcomes=12),
    target_stats=(TargetStat.THREE_POINTERS,)
    )

STEALS_MODEL = PlayerStatModelSpecification(
    name="steals",
    title="Steals",
    description="How many steals one player records in a game.",
    output=IntegerDistribution(minimum_value=0, outcomes=10),
    target_stats=(TargetStat.STEALS,)
    )

BLOCKS_MODEL = PlayerStatModelSpecification(
    name="blocks",
    title="Blocks",
    description="How many blocks one player records in a game.",
    output=IntegerDistribution(minimum_value=0, outcomes=10),
    target_stats=(TargetStat.BLOCKS,)
    )

TURNOVERS_MODEL = PlayerStatModelSpecification(
    name="turnovers",
    title="Turnovers",
    description="How many turnovers one player records in a game.",
    output=IntegerDistribution(minimum_value=0, outcomes=12),
    target_stats=(TargetStat.TURNOVERS,)
    )

POINTS_REBOUNDS_MODEL = PlayerStatModelSpecification(
    name="points_rebounds",
    title="Points and rebounds",
    description="The combined points and rebounds one player records.",
    output=IntegerDistribution(minimum_value=0, outcomes=70),
    target_stats=(TargetStat.POINTS, TargetStat.REBOUNDS)
    )

POINTS_ASSISTS_MODEL = PlayerStatModelSpecification(
    name="points_assists",
    title="Points and assists",
    description="The combined points and assists one player records.",
    output=IntegerDistribution(minimum_value=0, outcomes=70),
    target_stats=(TargetStat.POINTS, TargetStat.ASSISTS)
    )

REBOUNDS_ASSISTS_MODEL = PlayerStatModelSpecification(
    name="rebounds_assists",
    title="Rebounds and assists",
    description="The combined rebounds and assists one player records.",
    output=IntegerDistribution(minimum_value=0, outcomes=35),
    target_stats=(TargetStat.REBOUNDS, TargetStat.ASSISTS)
    )

STEALS_BLOCKS_MODEL = PlayerStatModelSpecification(
    name="steals_blocks",
    title="Steals and blocks",
    description="The combined steals and blocks one player records.",
    output=IntegerDistribution(minimum_value=0, outcomes=12),
    target_stats=(TargetStat.STEALS, TargetStat.BLOCKS)
    )

POINTS_REBOUNDS_ASSISTS_MODEL = PlayerStatModelSpecification(
    name="points_rebounds_assists",
    title="Points, rebounds and assists",
    description="The combined points, rebounds and assists one player records.",
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

MILESTONE_METRICS = (
    evaluation.PROBABILITY_OF_ACTUAL,
    evaluation.BRIER_SCORE,
    evaluation.CALIBRATION_ERROR
)
"""
What a rare yes or no answer is judged on, in place of the usual set.

Accuracy is left out on purpose. A triple double happens in about half a percent of games, so always
answering no scores 99.5% and a model that has learned nothing looks perfect. What separates a good
model from that one is the chance it puts on what actually happened, and whether that chance means
what it says.
"""

DOUBLE_DOUBLE_MODEL = PlayerStatModelSpecification(
    name="double_double",
    title="Double double",
    description="Whether a player records double figures in two statistics.",
    output=MILESTONE_OUTPUT,
    target_stats=MILESTONE_STATS,
    combination=DoubleFigureMilestone(stats_needed=2, predicted="double double chances"),
    published_metrics=MILESTONE_METRICS
    )

TRIPLE_DOUBLE_MODEL = PlayerStatModelSpecification(
    name="triple_double",
    title="Triple double",
    description="Whether a player records double figures in three statistics.",
    output=MILESTONE_OUTPUT,
    target_stats=MILESTONE_STATS,
    combination=DoubleFigureMilestone(stats_needed=3, predicted="triple double chances"),
    published_metrics=MILESTONE_METRICS
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

def union_feature_set() -> FeatureSet:
    """
    Every column any model of this family reads, resolved as one feature set.

    This is what the whole-league build is made over, so one build answers all fourteen models and
    adding a model adds no build. build_feature_set already takes the union of what each stat asks
    for, so this is a call rather than a second definition of the columns.
    """

    return build_feature_set(
        tuple(
            target_stat
            for specification in ALL_MODEL_SPECIFICATIONS.values()
            for target_stat in specification.target_stats
        )
    )

