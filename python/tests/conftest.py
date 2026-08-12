"""
What every test in this package needs before it imports anything from the project.

The stores name their database files when they are first imported, off the data directory in
nba_ml/paths.py, so the whole tree is pointed at a temporary directory here and no test can reach
the real one. That has to happen before the first nba_ml import, which is why it sits at the top of
this file rather than inside a fixture.
"""

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
    """Every test starts with nothing collected and nothing published."""

    shutil.rmtree(DATA_DIRECTORY, ignore_errors=True)
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # A published build is held in memory for the life of the process and told apart by a version
    # named to the second, so two tests publishing inside one second would share one.
    feature_store._held.clear()

    yield

def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(DATA_DIRECTORY, ignore_errors=True)
