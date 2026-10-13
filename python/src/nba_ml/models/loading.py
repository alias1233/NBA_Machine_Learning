"""Loads saved models from disk."""

import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from nba_ml.machine_learning import serialization
from nba_ml.machine_learning.architectures.gru_feed_forward import GRUFeedForward
from nba_ml.models.specifications import ModelSpecification

SEQUENCE_SCALER = 'sequence_scaler'
STATIC_SCALER = 'static_scaler'
SEQUENCE_COLUMNS = 'sequence_columns'
STATIC_COLUMNS = 'static_columns'
EVALUATION_SETTINGS = 'evaluation_settings'

Fingerprint = tuple[int, int]
"""A file's (modification time, size), used to detect when it changes."""

_held: dict[Path, tuple[Fingerprint, GRUFeedForward, dict[str, Any]]] = {}
_reading = threading.Lock()

def _fingerprint(model_file: Path) -> Fingerprint:
    written = model_file.stat()

    return (written.st_mtime_ns, written.st_size)

def load(model_file: Path) -> tuple[GRUFeedForward, dict[str, Any]]:
    """Loads a model and its saved parameters. The result is cached until the file changes."""

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
    """Returns True if the model was trained on the same columns its specification uses now."""

    feature_set = specification.get_feature_set()

    return all(
        saved.get(key) is None or list(saved[key]) == list(columns)
        for key, columns in (
            (SEQUENCE_COLUMNS, feature_set.sequence_columns),
            (STATIC_COLUMNS, feature_set.static_columns)
        )
    )

def can_load(specification: ModelSpecification) -> bool:
    """Returns True if the model has a saved file that matches its specification."""

    try:
        model, saved = load(specification.model_file())
    except Exception:
        return False

    return (
        model.output_dim == specification.output.length
        and model.sequence_count == specification.sequences_read
        and _reads_the_columns_it_was_fit_on(saved, specification)
    )

def trained_at(specification: ModelSpecification) -> datetime | None:
    """Returns when the model's file was last written, or None if it has no usable file."""

    if not can_load(specification):
        return None

    return datetime.fromtimestamp(specification.model_file().stat().st_mtime)
