"""
What each team game statistics model predicts, and what it would take to train one.

Every model here reads the same thing: a team's own past games, the opponent's, and what is known
about the game being predicted. That is the whole feature set, so the three cost one build between
them the way the player stats do.

Each range below was checked against the 105,030 collected team games and leaves out fewer than
0.02% of them, which is the room a distribution needs at its tails.

Every field these need is already collected, and every source considered for this project carries
it: stats.nba.com through nba_api, which is what collection uses today, BALLDONTLIE on its free
tier, SportsDataIO and Sportradar. None of them needs play-by-play, tracking or injury data, so no
new source has to be stood up before this family can be trained.
"""

from dataclasses import dataclass
from typing import ClassVar

from nba_ml.models.outputs import IntegerDistribution
from nba_ml.models.specifications import ModelSpecification

MODEL_CATEGORY = "team_game_stats"
"""Names the folder every model of this family is saved under."""

@dataclass(frozen=True)
class TeamGameStatModelSpecification(ModelSpecification):
    """One team game statistics model. Each answers about one thing, so each names its own."""

    model_category: ClassVar[str] = MODEL_CATEGORY

    output: IntegerDistribution
    predicted: str

    @property
    def predicts(self) -> tuple[str, ...]:
        return (self.predicted,)

POINT_DIFFERENTIAL_MODEL = TeamGameStatModelSpecification(
    name="point_differential",
    output=IntegerDistribution(minimum_value=-60, outcomes=121),
    predicted="point differential"
    )
"""How much a team wins or loses by. Its positive half is the chance the team wins."""

TEAM_POINTS_MODEL = TeamGameStatModelSpecification(
    name="team_points",
    output=IntegerDistribution(minimum_value=50, outcomes=121),
    predicted="team points"
    )
"""How many points one team scores."""

GAME_TOTAL_MODEL = TeamGameStatModelSpecification(
    name="game_total",
    output=IntegerDistribution(minimum_value=120, outcomes=201),
    predicted="game total"
    )
"""How many points both teams score together."""

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        POINT_DIFFERENTIAL_MODEL,
        TEAM_POINTS_MODEL,
        GAME_TOTAL_MODEL
    )
}

MODEL_NAMES = sorted(ALL_MODEL_SPECIFICATIONS)
