"""
Every model family, in one list.

A family is defined by what has to be named to ask it for an answer: a player, a team, or a game.
That is what decides which page a model is predicted on and what a request carries, so it is the line
worth drawing. Two families can be built on the same rows and still be two families, which is what
team statistics and game statistics are: one reads a game from a named side, the other reads the
whole game at once.

This is what the service reads to say which models exist and which can answer, so adding a family is
one folder beside this file and one entry in ALL_FAMILIES.

A model name is unique across every family, because a name is what a command line argument and a
saved file are given.
"""

from dataclasses import dataclass
from typing import Callable, Mapping

from nba_ml.models import loading
from nba_ml.models.game_stats import specifications as game_stat_specifications
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.models.specifications import ModelSpecification
from nba_ml.models.team_stats import specifications as team_stat_specifications

@dataclass(frozen=True)
class ModelFamily():
    """One group of models, and the little a caller needs to know without importing its internals."""

    name: str
    specifications: Mapping[str, ModelSpecification]
    is_published: Callable[[ModelSpecification], bool]
    """
    Whether a model can actually answer.

    Every family here saves one shape of file, so all of them check it with models/loading.py. A
    family that saves something else brings its own check rather than changing that one.
    """

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
    """The family a model belongs to and its specification, or None when no family names it."""

    for family in ALL_FAMILIES:
        specification = family.specifications.get(name)
        if specification is not None:
            return (family, specification)

    return None
