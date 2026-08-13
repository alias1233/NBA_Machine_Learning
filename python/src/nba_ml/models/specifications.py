"""
What every model, in every family, has in common.

A model is named, says what it answers about, and says what shape its answer has. That is all the
service needs to list it and serve it, so nothing here limits what a model may predict.

A family adds a subclass naming its category and holding whatever only that family needs.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Protocol

from nba_ml import paths
from nba_ml.models.outputs import ModelOutput

class FeatureColumns(Protocol):
    """
    What every family's feature set holds, which is all anything outside a family reads off one.

    A family resolves far more than this, and what it resolves is its own business. These two are
    named here because a saved model is checked against them. See nba_ml/models/loading.py.
    """

    sequence_columns: list[str]
    """Read for each of the subject's past games."""

    static_columns: list[str]
    """Read once, off the game being predicted."""

class GameSide(StrEnum):
    """One side of a game, which is what an answer belonging to a game names."""

    HOME = "home"
    AWAY = "away"

@dataclass(frozen=True)
class ModelSpecification():
    """
    One trained model: the name it is saved under, and the answer it gives.

    The name is what `nba-train --model` and `nba-predict --model` take, so two models predicting the
    same thing with different settings are two specifications with different names.
    """

    model_category: ClassVar[str]
    """The family this model belongs to. Set once per family, and it names the folder files sit in."""

    name: str
    output: ModelOutput
    """The shape of an answer. See nba_ml/models/outputs.py."""

    read_from: GameSide | None = field(default=None, kw_only=True)
    """
    Which side of the game a value above zero belongs to, for an answer with a direction.

    A point differential is read off the home team's row, so a positive one is the home team's
    margin and a caller has to say whose margin it is drawing. None where the answer names no side,
    either because it has no direction or because the request already named the subject.
    """

    category_sides: tuple[GameSide, ...] | None = field(default=None, kw_only=True)
    """
    Which side of the game each category names, in the order the output lists them.

    A category naming a side leads with that side's word, so a caller can put the team playing it in
    place of the word and turn "home win" into the team's own name. None where no category names a
    side, which is every yes or no answer.
    """

    def __post_init__(self):
        if self.category_sides is not None and len(self.category_sides) != self.output.length:
            raise ValueError(
                "Naming the side of each category takes one side per category, because the two are "
                "read together by position."
            )

    @property
    def predicts(self) -> tuple[str, ...]:
        """What this model answers about, in the words a reader sees."""

        raise NotImplementedError

    @property
    def sequences_read(self) -> int:
        """
        How many game histories one sample of this model reads.

        One unless the family says otherwise. A model asked about a whole game reads both teams, and
        a saved file fit on a different number of them cannot answer.
        """

        return 1

    def get_feature_set(self) -> FeatureColumns:
        """
        Which columns this model reads, resolved by the family that owns them.

        Resolve it once per run and pass it down, so that two models being built at the same time
        never share column state.
        """

        raise NotImplementedError

    def model_file(self) -> Path:
        return paths.model_file(self.model_category, self.name)

    def training_report_file(self) -> Path:
        return paths.training_report_file(self.model_category, self.name)

    def training_cache_file(self) -> Path:
        return paths.training_cache_file(self.model_category, self.name)

    def graphs_directory(self) -> Path:
        return paths.graphs_directory(self.model_category, self.name)
