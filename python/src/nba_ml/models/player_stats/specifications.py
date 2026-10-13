"""Defines the player stats models."""

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
"""Name of the folder this family's models are saved in."""

# Number of most recent games the GRU uses per prediction, or None for a player's entire history.
MAX_SEQUENCE_LENGTH: int | None = 50

@dataclass(frozen=True)
class PlayerStatModelSpecification(ClassifierModelSpecification):
    """Specification for a player stats model."""

    model_category: ClassVar[str] = MODEL_CATEGORY

    target_stats: tuple[TargetStat, ...]
    combination: StatCombination = StatTotal()
    """The method used to combine the target stats into the predicted value."""

    @property
    def predicts(self) -> tuple[str, ...]:
        return self.combination.predicts(self.target_stats)

    def get_feature_set(self) -> FeatureSet:
        """Returns the feature set for this model."""

        return build_feature_set(self.target_stats, self.combination)

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
"""The five stats that count towards a double-double or triple-double."""

MILESTONE_OUTPUT = CategoryDistribution(categories=MILESTONE_CATEGORIES)

MILESTONE_METRICS = (
    evaluation.PROBABILITY_OF_ACTUAL,
    evaluation.BRIER_SCORE,
    evaluation.CALIBRATION_ERROR
)
"""Metrics shown for the double-double and triple-double models instead of the defaults."""

DOUBLE_DOUBLE_MODEL = PlayerStatModelSpecification(
    name="double_double",
    title="Double-double",
    description="Whether a player records double figures in two statistics.",
    output=MILESTONE_OUTPUT,
    target_stats=MILESTONE_STATS,
    combination=DoubleFigureMilestone(stats_needed=2, predicted="double-double chances"),
    published_metrics=MILESTONE_METRICS
    )

TRIPLE_DOUBLE_MODEL = PlayerStatModelSpecification(
    name="triple_double",
    title="Triple-double",
    description="Whether a player records double figures in three statistics.",
    output=MILESTONE_OUTPUT,
    target_stats=MILESTONE_STATS,
    combination=DoubleFigureMilestone(stats_needed=3, predicted="triple-double chances"),
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
    """Returns one feature set with the columns of every model in this family."""

    return build_feature_set(
        tuple(
            target_stat
            for specification in ALL_MODEL_SPECIFICATIONS.values()
            for target_stat in specification.target_stats
        )
    )

