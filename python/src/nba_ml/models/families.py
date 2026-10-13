"""Lists every model family."""

from dataclasses import dataclass
from typing import Callable, Mapping

from nba_ml.models import loading
from nba_ml.models.game_stats import specifications as game_stat_specifications
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.models.specifications import ModelSpecification
from nba_ml.models.team_stats import specifications as team_stat_specifications

@dataclass(frozen=True)
class ModelFamily():
    """A group of models that take the same kind of request."""

    name: str
    specifications: Mapping[str, ModelSpecification]
    is_published: Callable[[ModelSpecification], bool]
    """Returns True if the model has a trained file that can be loaded."""

ALL_FAMILIES = (
    ModelFamily(
        player_stat_specifications.MODEL_CATEGORY,
        player_stat_specifications.ALL_MODEL_SPECIFICATIONS,
        loading.can_load
    ),
    ModelFamily(
        team_stat_specifications.MODEL_CATEGORY,
        team_stat_specifications.ALL_MODEL_SPECIFICATIONS,
        loading.can_load
    ),
    ModelFamily(
        game_stat_specifications.MODEL_CATEGORY,
        game_stat_specifications.ALL_MODEL_SPECIFICATIONS,
        loading.can_load
    )
)

ALL_MODEL_NAMES = sorted(name for family in ALL_FAMILIES for name in family.specifications)

def find_model(name: str) -> tuple[ModelFamily, ModelSpecification] | None:
    """Returns the family and specification of the model with the given name, or None if there isn't one."""

    for family in ALL_FAMILIES:
        specification = family.specifications.get(name)
        if specification is not None:
            return (family, specification)

    return None
