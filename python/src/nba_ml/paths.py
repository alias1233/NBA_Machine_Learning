"""File and directory paths used across the project."""

import os
from pathlib import Path

WORKSPACE_DIRECTORY = Path(__file__).resolve().parents[2]

DATA_DIRECTORY = Path(os.environ.get("NBA_ML_DATA_DIR", WORKSPACE_DIRECTORY / "data"))

DATABASE_DIRECTORY = DATA_DIRECTORY / "databases"
MODELS_DIRECTORY = DATA_DIRECTORY / "models"
TRAINING_CACHE_DIRECTORY = DATA_DIRECTORY / "training_cache"
FEATURE_BUILDS_DIRECTORY = DATA_DIRECTORY / "feature_builds"

SHOWCASE_FILE = DATA_DIRECTORY / "showcase.json"
"""Sample predictions for the home page, written by nba-showcase and served by the API."""

BACKUP_DIRECTORY = Path(os.environ.get("NBA_ML_BACKUP_DIR", DATA_DIRECTORY / "backups"))

def database_file(name: str) -> Path:
    return DATABASE_DIRECTORY / f"{name}.db"

def feature_build_directory(name: str) -> Path:
    """Directory containing every published version of a feature build."""

    return FEATURE_BUILDS_DIRECTORY / name

def model_directory(category: str, name: str) -> Path:
    return MODELS_DIRECTORY / category / name

def model_file(category: str, name: str) -> Path:
    return model_directory(category, name) / "model.pth"

def training_report_file(category: str, name: str) -> Path:
    return model_directory(category, name) / "training_report.txt"

def evaluation_file(category: str, name: str) -> Path:
    """File with the model's scores on its held-out games."""

    return model_directory(category, name) / "evaluation.json"

def published_model_files() -> list[Path]:
    """Returns every saved model file and its evaluation file, if it has one."""

    files = []
    for weights in MODELS_DIRECTORY.glob("*/*/model.pth"):
        if weights.is_file():
            files.append(weights)
            evaluation = weights.with_name("evaluation.json")
            if evaluation.is_file():
                files.append(evaluation)
    return sorted(files)

def graphs_directory(category: str, name: str) -> Path:
    return model_directory(category, name) / "graphs"

def training_cache_file(category: str, name: str) -> Path:
    return TRAINING_CACHE_DIRECTORY / category / name / "training_data.pth"
