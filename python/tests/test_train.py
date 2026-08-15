"""The training command's NBA-era selection and cached-build identity."""

import sys
from datetime import datetime

import pytest

from nba_ml import season
from nba_ml.cli import train
from nba_ml.models import classifier_training
from nba_ml.models.team_stats import specifications, training


def test_the_training_start_season_reaches_the_selected_family(monkeypatch):
    called = {}
    monkeypatch.setattr(
        sys,
        "argv",
        ["nba-train", "--model", "team_points", "--training-start-season", str(season.COLLECTION_START_SEASON)]
    )
    monkeypatch.setitem(train.TRAINERS, specifications.MODEL_CATEGORY, lambda *args, **kwargs: called.update(kwargs))

    train.main()

    assert called["training_start_date"] == datetime(
        season.COLLECTION_START_SEASON, season.SEASON_START_MONTH, 1
    )


def test_the_training_start_season_is_limited_to_nba_milestones(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["nba-train", "--model", "team_points", "--training-start-season", "1995"])

    with pytest.raises(SystemExit):
        train.main()


def test_a_training_cache_is_not_shared_between_eras():
    inputs = training._training_inputs(specifications.TEAM_POINTS_MODEL)

    assert classifier_training._describe_build(
        specifications.TEAM_POINTS_MODEL, inputs, datetime(2019, 10, 1)
    ) != classifier_training._describe_build(
        specifications.TEAM_POINTS_MODEL, inputs, datetime(2020, 10, 1)
    )
