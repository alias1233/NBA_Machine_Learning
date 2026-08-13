"""
Reading a saved model back off disk, for any family.

A model file holds the network's shape, its weights, the two scalers fitted with it, and the columns
it was fit on, so a model can never be mismatched with any of them. Training writes the layout named
here and inference reads it.
"""

import threading
from pathlib import Path
from typing import Any

from nba_ml.machine_learning import serialization
from nba_ml.machine_learning.architectures.gru_feed_forward import GRUFeedForward
from nba_ml.models.specifications import ModelSpecification

SEQUENCE_SCALER = 'sequence_scaler'
STATIC_SCALER = 'static_scaler'
SEQUENCE_COLUMNS = 'sequence_columns'
STATIC_COLUMNS = 'static_columns'

Fingerprint = tuple[int, int]
"""When a file was last written and how big it is, which is what tells one file's contents apart."""

_held: dict[Path, tuple[Fingerprint, GRUFeedForward, dict[str, Any]]] = {}
_reading = threading.Lock()

def _fingerprint(model_file: Path) -> Fingerprint:
    written = model_file.stat()

    return (written.st_mtime_ns, written.st_size)

def load(model_file: Path) -> tuple[GRUFeedForward, dict[str, Any]]:
    """
    Reads a model and its scalers off disk once and keeps them, so a service answering many requests
    pays for the read once. Predicting never writes to either.

    A republished file is picked up without a restart. The file's own timestamp and size are read on
    every call, which is one stat against a 6 ms read, and a file that has changed is read again.

    Returns:
        (the model, everything the file holds, which is where the scalers are read from)
    """

    fingerprint = _fingerprint(model_file)

    with _reading:
        held = _held.get(model_file)

        if held is None or held[0] != fingerprint:
            parameters_dict = serialization.load_data_from_file(model_file)
            held = (
                fingerprint,
                GRUFeedForward.load_from_saved_parameters_dict(parameters_dict),
                parameters_dict
            )
            _held[model_file] = held

        return (held[1], held[2])

def _reads_the_columns_it_was_fit_on(
    saved: dict[str, Any],
    specification: ModelSpecification
    ) -> bool:
    """
    Whether the file was fit on the columns its specification now asks for.

    Nothing about a saved file changes when a column is added or removed, so without this a model
    fit on a feature set that has since moved reports as publishable and then fails at the first
    matrix multiply. Every model file went stale that way on 2026-08-11.

    A file written before the columns were saved beside the weights carries neither list, and is
    taken at its word rather than refused, so adding this check orphaned nothing already trained.
    """

    feature_set = specification.get_feature_set()

    return all(
        saved.get(key) is None or list(saved[key]) == list(columns)
        for key, columns in (
            (SEQUENCE_COLUMNS, feature_set.sequence_columns),
            (STATIC_COLUMNS, feature_set.static_columns)
        )
    )

def can_load(specification: ModelSpecification) -> bool:
    """
    Whether this model has a file that can actually answer what its specification promises.

    A specification can name a model that was never trained, or one saved by code old enough that
    the file no longer loads. A caller serving requests checks here rather than failing part way
    through a prediction. The load is cached, so a model that works costs nothing to check.

    What the file holds is checked as well as the read. A model fit before its range changed would
    answer with the old number of values under the new range's labels, one fit on a different number
    of game histories cannot be fed at all, and one fit on columns the build no longer produces
    cannot be fed either. All three read as a working file and are caught here.
    """

    try:
        model, saved = load(specification.model_file())
    except Exception:
        return False

    return (
        model.output_dim == specification.output.length
        and model.sequence_count == specification.sequences_read
        and _reads_the_columns_it_was_fit_on(saved, specification)
    )
