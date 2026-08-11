"""
What every model, in every family, has in common.

A model is named, says what it answers about, and says what shape its answer has. That is all the
service needs to list it and serve it, so nothing here limits what a model may predict.

A family adds a subclass naming its category and holding whatever only that family needs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from nba_ml import paths
from nba_ml.models.outputs import ModelOutput

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

    def model_file(self) -> Path:
        return paths.model_file(self.model_category, self.name)

    def training_report_file(self) -> Path:
        return paths.training_report_file(self.model_category, self.name)

    def training_cache_file(self) -> Path:
        return paths.training_cache_file(self.model_category, self.name)

    def graphs_directory(self) -> Path:
        return paths.graphs_directory(self.model_category, self.name)
