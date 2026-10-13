"""Base model specification shared by every family."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Protocol

from nba_ml import paths
from nba_ml.models import metrics
from nba_ml.models.outputs import ModelOutput

class FeatureColumns(Protocol):
    """The fields every family's feature set must have."""

    sequence_columns: list[str]
    """Columns taken from each of the subject's past games."""

    static_columns: list[str]
    """Columns taken from the game being predicted."""

class GameSide(StrEnum):
    """The home or away team of a game."""

    HOME = "home"
    AWAY = "away"

@dataclass(frozen=True)
class ModelSpecification():
    """Defines a model: its name, how it is described and what it outputs."""

    model_category: ClassVar[str]
    """The model's family. Also the name of the folder its files are saved in."""

    name: str
    title: str = field(kw_only=True)
    """Short display name shown on the site."""

    description: str = field(kw_only=True)
    """Short description shown on the site."""

    output: ModelOutput
    """The model's output type."""

    read_from: GameSide | None = field(default=None, kw_only=True)
    """For signed outputs such as point differential, the team a positive value belongs to."""

    category_sides: tuple[GameSide, ...] | None = field(default=None, kw_only=True)
    """The team each output category refers to, in the same order as the categories."""

    published_metrics: tuple[str, ...] | None = field(default=None, kw_only=True)
    """Metrics shown for this model, most important first. None uses the defaults for its output type."""

    def __post_init__(self):
        unknown = sorted(set(self.published_metrics or ()) - set(metrics.ALL_METRICS))
        if unknown:
            raise ValueError(
                f"{self.name} publishes figures nothing describes: {', '.join(unknown)}. "
                "Add them to metrics.ALL_METRICS or name them the way it does."
            )

        if self.category_sides is not None and len(self.category_sides) != self.output.length:
            raise ValueError(
                "Naming the side of each category takes one side per category, because the two are "
                "read together by position."
            )

    @property
    def predicts(self) -> tuple[str, ...]:
        """Display names of what this model predicts."""

        raise NotImplementedError

    @property
    def reported_metrics(self) -> tuple[str, ...]:
        """Returns the metrics shown for this model."""

        if self.published_metrics is not None:
            return self.published_metrics

        return metrics.default_published_metrics(self.output)

    @property
    def sequences_read(self) -> int:
        """Number of game sequences in each of this model's samples."""

        return 1

    def get_feature_set(self) -> FeatureColumns:
        """Returns the model's feature set. Implemented by each family."""

        raise NotImplementedError

    def model_file(self) -> Path:
        return paths.model_file(self.model_category, self.name)

    def training_report_file(self) -> Path:
        return paths.training_report_file(self.model_category, self.name)

    def evaluation_file(self) -> Path:
        return paths.evaluation_file(self.model_category, self.name)

    def training_cache_file(self) -> Path:
        return paths.training_cache_file(self.model_category, self.name)

    def graphs_directory(self) -> Path:
        return paths.graphs_directory(self.model_category, self.name)
