"""
Every model family, in one list.

A family is a group of models that answer the same kind of question and share one feature set. This
is what the service reads to say which models exist and which can answer, so adding a family is one
folder beside this file and one entry in ALL_FAMILIES.

A model name is unique across every family, because a name is what a command line argument and a
saved file are given.
"""

from dataclasses import dataclass
from typing import Callable, Mapping

from nba_ml.models.player_stats import inference as player_stat_inference
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.models.specifications import ModelSpecification
from nba_ml.models.team_game_stats import specifications as team_game_stat_specifications

def _has_saved_model(specification: ModelSpecification) -> bool:
    """Whether a trained file exists, which is as much as a family with no loader yet can say."""

    return specification.model_file().exists()

@dataclass(frozen=True)
class ModelFamily():
    """One group of models, and the little a caller needs to know without importing its internals."""

    name: str
    specifications: Mapping[str, ModelSpecification]
    is_published: Callable[[ModelSpecification], bool] = _has_saved_model
    """Whether a model can actually answer. A family with a loader checks that its file still reads."""

ALL_FAMILIES = (
    ModelFamily(
        player_stat_specifications.MODEL_CATEGORY,
        player_stat_specifications.ALL_MODEL_SPECIFICATIONS,
        player_stat_inference.can_load
    ),
    ModelFamily(
        team_game_stat_specifications.MODEL_CATEGORY,
        team_game_stat_specifications.ALL_MODEL_SPECIFICATIONS
    )
)

ALL_MODEL_NAMES = sorted(name for family in ALL_FAMILIES for name in family.specifications)
