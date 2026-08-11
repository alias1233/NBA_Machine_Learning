"""
Reading a saved model back off disk, for any family.

A model file holds the network's shape, its weights, and the two scalers fitted with it, so a model
and its scalers can never be mismatched. Training writes the layout named here and inference reads
it.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from nba_ml.machine_learning import serialization
from nba_ml.machine_learning.architectures.gru_feed_forward import GRUFeedForward
from nba_ml.models.specifications import ModelSpecification

SEQUENCE_SCALER = 'sequence_scaler'
STATIC_SCALER = 'static_scaler'

@lru_cache(maxsize=None)
def load(model_file: Path) -> tuple[GRUFeedForward, dict[str, Any]]:
    """
    Reads a model and its scalers off disk once and keeps them, so a service answering many requests
    pays for the read once. Predicting never writes to either.

    Returns:
        (the model, everything the file holds, which is where the scalers are read from)
    """

    parameters_dict = serialization.load_data_from_file(model_file)

    return (GRUFeedForward.load_from_saved_parameters_dict(parameters_dict), parameters_dict)

def can_load(specification: ModelSpecification) -> bool:
    """
    Whether this model has a file that can actually answer what its specification promises.

    A specification can name a model that was never trained, or one saved by code old enough that the
    file no longer loads. A caller serving requests checks here rather than failing part way through
    a prediction. The load is cached, so a model that works costs nothing to check.

    The shape is checked as well as the read, because a saved file carries its own. A model fit
    before its range changed still loads, and would answer with the old number of values under the
    new range's labels, which reads as a working answer about the wrong outcomes. A model fit on a
    different number of game histories cannot be fed at all, and this is where that is found rather
    than part way through a request.
    """

    try:
        model, _ = load(specification.model_file())
    except Exception:
        return False

    return (
        model.output_dim == specification.output.length
        and model.sequence_count == specification.sequences_read
    )
