"""
What the team point differential model predicts.

The outcomes run from a 60 point loss to a 60 point win, which covers every result in the collected
data with room to spare. Nothing reads these numbers yet.
"""

from dataclasses import dataclass
from typing import ClassVar

from nba_ml.models.specifications import ModelSpecification

MODEL_CATEGORY = "team_point_differential"
"""Names the folder every model of this family is saved under."""

@dataclass(frozen=True)
class TeamPointDifferentialModelSpecification(ModelSpecification):
    model_category: ClassVar[str] = MODEL_CATEGORY

    @property
    def predicts(self) -> tuple[str, ...]:
        return ("point differential",)

POINT_DIFFERENTIAL_MODEL = TeamPointDifferentialModelSpecification(
    name="point_differential",
    minimum_value=-60,
    outcomes=121
    )

ALL_MODEL_SPECIFICATIONS = {POINT_DIFFERENTIAL_MODEL.name: POINT_DIFFERENTIAL_MODEL}

MODEL_NAMES = sorted(ALL_MODEL_SPECIFICATIONS)
