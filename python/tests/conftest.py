"""Test setup. Points the data directory at a temporary folder before nba_ml is imported."""

import os
import shutil
import tempfile
from pathlib import Path

DATA_DIRECTORY = Path(tempfile.mkdtemp(prefix="nba-ml-tests-"))
os.environ["NBA_ML_DATA_DIR"] = str(DATA_DIRECTORY)

import pytest

from nba_ml.feature_engineering import feature_store

@pytest.fixture(autouse=True)
def empty_data_directory():
    """Clears the data directory before each test."""

    shutil.rmtree(DATA_DIRECTORY, ignore_errors=True)
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    feature_store._held.clear()

    yield

def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(DATA_DIRECTORY, ignore_errors=True)
