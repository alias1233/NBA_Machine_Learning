"""
Where everything the pipeline reads and writes lives.

Paths are anchored to the workspace rather than the current directory, so a command works from
anywhere. Set NBA_ML_DATA_DIR to point the whole tree somewhere else, which is what a deployment
with a mounted volume does.
"""

import os
from pathlib import Path

WORKSPACE_DIRECTORY = Path(__file__).resolve().parents[2]

DATA_DIRECTORY = Path(os.environ.get("NBA_ML_DATA_DIR", WORKSPACE_DIRECTORY / "data"))

DATABASE_DIRECTORY = DATA_DIRECTORY / "databases"
MODELS_DIRECTORY = DATA_DIRECTORY / "models"
TRAINING_CACHE_DIRECTORY = DATA_DIRECTORY / "training_cache"
FEATURE_BUILDS_DIRECTORY = DATA_DIRECTORY / "feature_builds"

def database_file(name: str) -> Path:
    return DATABASE_DIRECTORY / f"{name}.db"

def feature_build_directory(name: str) -> Path:
    """
    Every published version of one whole-league feature build, kept side by side.

    A build is published by writing a new version beside the old one, so a failed job leaves the
    previous build where the service can still read it.
    """

    return FEATURE_BUILDS_DIRECTORY / name

def model_directory(category: str, name: str) -> Path:
    """Everything one trained model produces sits together: the weights, its report, its graphs."""

    return MODELS_DIRECTORY / category / name

def model_file(category: str, name: str) -> Path:
    return model_directory(category, name) / "model.pth"

def training_report_file(category: str, name: str) -> Path:
    return model_directory(category, name) / "training_report.txt"

def graphs_directory(category: str, name: str) -> Path:
    return model_directory(category, name) / "graphs"

def training_cache_file(category: str, name: str) -> Path:
    """The preprocessed training build, kept out of the model directory because it is disposable."""

    return TRAINING_CACHE_DIRECTORY / category / name / "training_data.pth"
