"""
What every model, in every family, has in common.

Every model here answers with a probability for each whole number outcome, so an answer has the same
shape whatever is being predicted. That is what lets the service list and serve a family without
knowing anything about what it predicts.

A family adds a subclass naming its category and holding whatever only that family needs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from nba_ml import paths

@dataclass(frozen=True)
class ModelSpecification():
    """
    One trained model: the name it is saved under, and the outcomes it answers with.

    The name is what `nba-train --model` and `nba-predict --model` take, so two models predicting the
    same thing with different settings are two specifications with different names.
    """

    model_category: ClassVar[str]
    """The family this model belongs to. Set once per family, and it names the folder files sit in."""

    name: str
    minimum_value: int
    """The outcome the first predicted probability stands for."""

    outcomes: int
    """How many whole number outcomes the model gives a probability for."""

    @property
    def predicts(self) -> tuple[str, ...]:
        """What this model answers about, in the words a reader sees."""

        raise NotImplementedError

    def model_file(self) -> Path:
        return paths.model_file(self.model_category, self.name)

    def training_report_file(self) -> Path:
        return paths.training_report_file(self.model_category, self.name)

    def training_cache_file(self) -> Path:
        return paths.training_cache_file(self.model_category, self.name)

    def graphs_directory(self) -> Path:
        return paths.graphs_directory(self.model_category, self.name)
