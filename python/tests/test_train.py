"""The training command's NBA-era selection, its split settings, and what a finished run leaves behind."""

import sys
from dataclasses import replace
from datetime import datetime

import pytest

from nba_ml import season
from nba_ml.api.app import family_info_models, model_evaluation
from nba_ml.cli import train
from nba_ml.feature_engineering.samples import EvaluationSplit, SplitKey
from nba_ml.machine_learning import evaluation
from nba_ml.models import classifier_training, metrics
from nba_ml.models.game_stats import training as game_stat_training
from nba_ml.models.game_stats import specifications as game_stat_specifications
from nba_ml.models.player_stats import training as player_stat_training
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.models.team_stats import specifications, training
from nba_ml.stores import team_games

import fake_data


A_SPLIT = classifier_training.default_evaluation_split()


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


def test_the_split_settings_reach_the_selected_family(monkeypatch):
    """Pinning the day is what scores several models on exactly the same games across two days."""

    called = {}
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nba-train",
            "--model", "team_points",
            "--evaluation-start", "2025-08-01",
            "--validation-fraction", "0.25"
        ]
    )
    monkeypatch.setitem(train.TRAINERS, specifications.MODEL_CATEGORY, lambda *args, **kwargs: called.update(kwargs))

    train.main()

    assert called["evaluation_split"].start_date == datetime(2025, 8, 1)
    assert called["evaluation_split"].validation_fraction == 0.25


def test_a_validation_fraction_that_is_not_a_share_is_refused(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["nba-train", "--model", "team_points", "--validation-fraction", "2"]
    )

    with pytest.raises(SystemExit):
        train.main()


def test_the_evaluation_period_defaults_to_the_last_year():
    started = classifier_training.default_evaluation_start_date().date()

    assert (season.today() - started).days in (365, 366)


def test_a_training_cache_is_not_shared_between_eras():
    inputs = training._training_inputs(specifications.TEAM_POINTS_MODEL)

    assert classifier_training._describe_build(
        specifications.TEAM_POINTS_MODEL, inputs, datetime(2019, 10, 1), A_SPLIT
    ) != classifier_training._describe_build(
        specifications.TEAM_POINTS_MODEL, inputs, datetime(2020, 10, 1), A_SPLIT
    )


def test_a_training_cache_is_not_shared_between_splits():
    """
    A saved build holds the finished splits and nothing about them can be read back out of it, so a
    run under new split settings has to rebuild rather than fit and score itself on the old ones.
    """

    model = specifications.TEAM_POINTS_MODEL
    inputs = training._training_inputs(model)
    era = datetime(2019, 10, 1)
    described = classifier_training._describe_build(model, inputs, era, A_SPLIT)

    moved = [
        replace(A_SPLIT, start_date=datetime(2020, 1, 1)),
        replace(A_SPLIT, validation_fraction=0.25),
        replace(A_SPLIT, split_on=SplitKey.GAME),
        replace(A_SPLIT, seed=A_SPLIT.seed + 1)
    ]

    assert all(
        classifier_training._describe_build(model, inputs, era, changed) != described
        for changed in moved
    )
    assert classifier_training._describe_build(model, inputs, era, A_SPLIT, chunk_step_size=2) != described


def test_only_models_with_nothing_servable_are_selected_by_a_day_in_the_past(monkeypatch):
    """
    A day far in the past is what "train whatever nothing can serve" is asked for, so a model with a
    working file has to be left alone however old that file is.
    """

    trained = specifications.TEAM_POINTS_MODEL
    monkeypatch.setattr(
        train.loading,
        "trained_at",
        lambda model: datetime(2020, 1, 1) if model.name == trained.name else None
    )

    selected = train.models_trained_before(datetime(1900, 1, 1))

    assert trained.name not in [model.name for model in selected]
    assert len(selected) == len(train.families.ALL_MODEL_NAMES) - 1


def test_a_model_trained_before_the_given_day_is_retrained(monkeypatch):
    monkeypatch.setattr(train.loading, "trained_at", lambda model: datetime(2026, 8, 15))

    assert len(train.models_trained_before(datetime(2026, 8, 16))) == len(train.families.ALL_MODEL_NAMES)
    assert train.models_trained_before(datetime(2026, 8, 14)) == []


def test_retraining_since_a_day_fits_every_selected_model_on_the_same_games(monkeypatch):
    """
    One run, many models. The held-back games are worked out once, so a batch crossing midnight
    scores its last model on the same games as its first.
    """

    fitted = []
    monkeypatch.setattr(sys, "argv", ["nba-train", "--retrain-since", "2026-08-16", "--no-cache"])
    monkeypatch.setattr(train.loading, "trained_at", lambda model: None)
    for category in train.TRAINERS:
        monkeypatch.setitem(
            train.TRAINERS,
            category,
            lambda model, **kwargs: fitted.append((model.name, kwargs["evaluation_split"]))
        )

    train.main()

    assert [name for name, _ in fitted] == [
        model.name for model in train.models_trained_before(datetime(2026, 8, 16))
    ]
    assert len({split for _, split in fitted}) == 1


def test_a_model_that_fails_does_not_stop_the_rest_of_a_batch(monkeypatch):
    """A batch of eighteen models is hours of work, so one failure is reported and not obeyed."""

    fitted = []
    monkeypatch.setattr(sys, "argv", ["nba-train", "--retrain-since", "2026-08-16"])
    monkeypatch.setattr(train.loading, "trained_at", lambda model: None)

    def train_one(model, **kwargs):
        if model.name == "team_points":
            raise RuntimeError("no data")

        fitted.append(model.name)

    for category in train.TRAINERS:
        monkeypatch.setitem(train.TRAINERS, category, train_one)

    with pytest.raises(SystemExit, match="team_points"):
        train.main()

    assert len(fitted) == len(train.families.ALL_MODEL_NAMES) - 1


def test_naming_a_model_and_a_day_at_once_is_refused(monkeypatch):
    """The two answer the same question, so a run taking both would have to pick one silently."""

    monkeypatch.setattr(
        sys, "argv", ["nba-train", "--model", "team_points", "--retrain-since", "2026-08-16"]
    )

    with pytest.raises(SystemExit):
        train.main()


def _one_epoch(model_specification):
    """The same model fitted for a single epoch, which is all a test of the plumbing needs."""

    parameters = model_specification.training_parameters

    return replace(
        model_specification,
        training_parameters=replace(
            parameters,
            configuration=replace(parameters.configuration, epochs=1, log_interval=0)
        )
    )


def test_a_finished_run_writes_a_held_out_score_the_service_reads_back():
    """
    The whole chain, end to end on the made up league: fit, score the games the run never read,
    write them down, and serve them on the family Info page.

    A run that scored its own validation games would report a number nobody should publish, so what
    matters here is that the split named in the file is the held-out one.
    """

    team_games.store(fake_data.team_game_frame())
    model_specification = _one_epoch(specifications.TEAM_POINTS_MODEL)

    result = training.train(
        model_specification,
        use_cached_build=False,
        save_cached_build=False,
        print_debug=False,
        training_start_date=datetime(fake_data.SEASON_YEAR, season.SEASON_START_MONTH, 1),
        evaluation_split=EvaluationSplit(start_date=datetime(2024, 10, 27))
    )

    assert result.evaluation is not None
    assert result.evaluation.scored_on == metrics.TEST_SPLIT_LABEL
    assert result.evaluation.samples > 0
    assert result.evaluation.first_game <= result.evaluation.last_game

    # Every figure the answer's shape publishes was scored, and the floor was scored on the same games.
    written = metrics.read(model_specification.evaluation_file())
    assert written is not None
    assert set(model_specification.reported_metrics) <= set(written.metrics)
    assert set(written.floor) <= set(written.metrics)
    assert evaluation.EXPECTED_VALUE_MAE in written.floor

    assert any(card.name == "team_points" for card in family_info_models("team_stats"))

    served = model_evaluation("team_stats", "team_points")
    assert served is not None
    assert [metric.key for metric in served.metrics] == list(model_specification.reported_metrics)


def test_a_run_whose_evaluation_period_holds_no_game_stops_rather_than_reporting_nothing():
    """
    An empty validation split picks the stopping epoch out of nothing and an empty test split scores
    the model on nothing. Neither says a word on its own, so the run is refused instead.
    """

    team_games.store(fake_data.team_game_frame())

    with pytest.raises(ValueError, match="validation and test split holds no samples"):
        training.train(
            _one_epoch(specifications.TEAM_POINTS_MODEL),
            use_cached_build=False,
            save_cached_build=False,
            print_debug=False,
            training_start_date=datetime(fake_data.SEASON_YEAR, season.SEASON_START_MONTH, 1),
            evaluation_split=EvaluationSplit(start_date=datetime(2030, 1, 1))
        )


def test_each_family_splits_its_evaluation_games_on_what_it_can_halve():
    """
    A thousand players halve cleanly and thirty teams do not, so the two families answer differently
    and the answer belongs to the family rather than to a run.
    """

    player_inputs = player_stat_training._training_inputs(
        player_stat_specifications.POINTS_MODEL
    )
    game_inputs = game_stat_training._training_inputs(
        game_stat_specifications.POINT_DIFFERENTIAL_MODEL
    )
    team_inputs = training._training_inputs(specifications.TEAM_POINTS_MODEL)

    assert player_inputs.split_on is SplitKey.SUBJECT
    assert game_inputs.split_on is SplitKey.GAME
    assert team_inputs.split_on is SplitKey.GAME
