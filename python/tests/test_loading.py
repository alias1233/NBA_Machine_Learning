"""
Which saved model files a family is willing to serve.

A saved file always loads. What it cannot say for itself is whether it still answers the question its
specification now asks, so every mismatch here reads as a working model until it is checked: an
answer of the wrong width, a file fit on a different number of game histories, and a file fit on
columns the build no longer produces. The last one made every model file stale on 2026-08-11.

The other half is the opposite worry. A file republished while the service is running has to be
noticed, or a freshly trained model reads as the old one until a restart.
"""

from dataclasses import dataclass
from typing import ClassVar

import pytest
import torch.nn as nn

from nba_ml.machine_learning import serialization
from nba_ml.machine_learning.architectures.feed_forward import LayerParameters
from nba_ml.machine_learning.architectures.gru_feed_forward import GRUFeedForward
from nba_ml.models import loading
from nba_ml.models.outputs import IntegerDistribution
from nba_ml.models.specifications import ModelSpecification

SEQUENCE_COLUMNS = ["POINTS", "REBOUNDS"]
STATIC_COLUMNS = ["REST", "HOME_OR_AWAY"]

@dataclass(frozen=True)
class FakeFeatureSet():
    sequence_columns: list[str]
    static_columns: list[str]

@dataclass(frozen=True)
class FakeSpecification(ModelSpecification):
    """A model of a family that exists only here, so nothing real has to be trained to check this."""

    model_category: ClassVar[str] = "tests"

    features: FakeFeatureSet = FakeFeatureSet(SEQUENCE_COLUMNS, STATIC_COLUMNS)

    def get_feature_set(self) -> FakeFeatureSet:
        return self.features

SPECIFICATION = FakeSpecification("saved", IntegerDistribution(minimum_value=0, outcomes=4))

def build_model(output_dim: int = 4, sequence_count: int = 1) -> GRUFeedForward:
    return GRUFeedForward(
        sequence_input_dim=len(SEQUENCE_COLUMNS),
        static_input_dim=len(STATIC_COLUMNS),
        output_dim=output_dim,
        hidden_layers=[LayerParameters(4, nn.ReLU(), False, 0.0)],
        gru_hidden_dim=4,
        sequence_count=sequence_count
    )

def publish(model: GRUFeedForward, columns: dict | None = None):
    """Writes a model file where the specification looks for one, as training would."""

    serialization.save_data_to_file(
        SPECIFICATION.model_file(),
        {
            **model.get_save_parameters_dict(),
            loading.SEQUENCE_COLUMNS: SEQUENCE_COLUMNS,
            loading.STATIC_COLUMNS: STATIC_COLUMNS,
            **(columns or {})
        }
    )

@pytest.fixture(autouse=True)
def forget_held_models():
    """A model is held for the life of the process, and every test here writes to one path."""

    loading._held.clear()

    yield

def test_a_model_fit_on_what_its_specification_asks_for_is_publishable():
    publish(build_model())

    assert loading.can_load(SPECIFICATION)

def test_a_model_that_was_never_trained_is_not_publishable():
    assert not loading.can_load(SPECIFICATION)

def test_a_model_answering_a_different_number_of_outcomes_is_not_publishable():
    publish(build_model(output_dim=6))

    assert not loading.can_load(SPECIFICATION)

def test_a_model_fit_on_a_different_number_of_histories_is_not_publishable():
    publish(build_model(sequence_count=2))

    assert not loading.can_load(SPECIFICATION)

def test_a_model_fit_on_columns_the_build_no_longer_holds_is_not_publishable():
    """The check this file exists for. Nothing else about the file changes when a column moves."""

    publish(build_model(), {loading.SEQUENCE_COLUMNS: SEQUENCE_COLUMNS + ["ASSISTS"]})

    assert not loading.can_load(SPECIFICATION)

def test_a_model_fit_on_reordered_static_columns_is_not_publishable():
    publish(build_model(), {loading.STATIC_COLUMNS: list(reversed(STATIC_COLUMNS))})

    assert not loading.can_load(SPECIFICATION)

def test_a_file_saved_before_columns_were_recorded_is_taken_at_its_word():
    """Backwards compatible on purpose, so adding the check orphaned no model already trained."""

    serialization.save_data_to_file(SPECIFICATION.model_file(), build_model().get_save_parameters_dict())

    assert loading.can_load(SPECIFICATION)

def test_a_republished_file_is_read_again_rather_than_answered_from_memory():
    """Publishing a model is copying a file in, and the service is not restarted for it."""

    publish(build_model())
    first, _ = loading.load(SPECIFICATION.model_file())

    assert loading.load(SPECIFICATION.model_file())[0] is first

    publish(build_model(output_dim=6))
    republished, _ = loading.load(SPECIFICATION.model_file())

    assert republished is not first
    assert republished.output_dim == 6
