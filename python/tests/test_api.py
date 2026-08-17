from datetime import datetime, timedelta

from fastapi import HTTPException

from nba_ml import season
from nba_ml.api.app import (
    ACTIVE_TEAM_WINDOW,
    all_models,
    all_teams,
    family_about_models,
    model_evaluation
)
from nba_ml.machine_learning import evaluation
from nba_ml.models import metrics
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.stores import team_games, teams

import fake_data
import pytest


def test_only_teams_still_playing_are_offered():
    """The archive holds teams that stopped playing decades ago, and none of them can be predicted."""

    league = fake_data.teams_frame()
    league.loc[len(league)] = {
        teams.TEAM_ID.category_name: 99,
        teams.ABBREVIATION.category_name: "EAS",
        teams.TEAM_NAME.category_name: "Eastport Engines"
    }

    teams.store(league)
    team_games.store(fake_data.team_game_frame())

    # Its one game is far enough behind the newest one held that the team reads as gone.
    gone = fake_data.team_game_frame().head(1).copy()
    gone[team_games.TEAM_ID.category_name] = 99
    gone[team_games.GAME_ID.category_name] = fake_data.game_id(99)
    gone[team_games.GAME_DATE.category_name] = season.to_date_string(
        fake_data.SEASON_GAMES[-1].day - ACTIVE_TEAM_WINDOW - timedelta(days=1)
    )

    team_games.store(gone)

    assert {team.abbreviation for team in all_teams()} == {team.abbreviation for team in fake_data.TEAMS}


def test_no_team_is_offered_when_no_game_is_collected():
    teams.store(fake_data.teams_frame())

    assert all_teams() == []


def test_model_about_copy_only_arrives_on_the_family_endpoint():
    catalogue = [model.model_dump() for model in all_models()]
    about_models = [model.model_dump() for model in family_about_models("player_stats")]

    assert all("title" not in model and "description" not in model for model in catalogue)
    assert all(
        {"name", "title", "description", "published"} == model.keys() for model in about_models
    )
    assert len(about_models) == 14


def test_unknown_model_family_has_no_about_catalogue():
    with pytest.raises(HTTPException, match="No model family is named unknown") as raised:
        family_about_models("unknown")

    assert raised.value.status_code == 404


def _score(specification, **scored: float):
    """Writes a scored file beside a model, as a finished training run would."""

    metrics.write(
        specification.evaluation_file(),
        metrics.ModelEvaluation(
            model=specification.name,
            scored_on=metrics.TEST_SPLIT_LABEL,
            samples=1234,
            first_game="2025-10-22",
            last_game="2026-06-13",
            evaluated=datetime(2026, 8, 16, 12).isoformat(timespec="seconds"),
            metrics=dict(scored),
            floor={evaluation.EXPECTED_VALUE_MAE: 5.5}
        )
    )


def test_a_model_with_no_score_is_still_offered_without_figures():
    assert any(card.name == "assists" for card in family_about_models("player_stats"))
    assert model_evaluation("player_stats", "assists") is None


def test_an_unknown_model_has_no_evaluation_to_read():
    with pytest.raises(HTTPException, match="No model named nothing is in the player_stats family"):
        model_evaluation("player_stats", "nothing")


def test_a_scored_model_returns_only_the_figures_it_chose_in_its_own_order():
    """
    Accuracy on a triple double is 99.5% however bad the model is, so that model leaves it out. What
    reaches the site is the model's own choice and nothing else.
    """

    _score(
        player_stat_specifications.TRIPLE_DOUBLE_MODEL,
        **{
            evaluation.ACCURACY: 0.9953,
            evaluation.PROBABILITY_OF_ACTUAL: 0.991,
            evaluation.BRIER_SCORE: 0.0079,
            evaluation.CALIBRATION_ERROR: 0.004
        }
    )

    scored = model_evaluation("player_stats", "triple_double")

    assert scored is not None
    assert [metric.key for metric in scored.metrics] == list(
        player_stat_specifications.MILESTONE_METRICS
    )
    assert scored.samples == 1234
    assert scored.scored_on == metrics.TEST_SPLIT_LABEL


def test_a_figure_the_run_did_not_score_is_left_out_rather_than_sent_as_a_blank():
    """A model fitted before its answer shape gained a figure still describes what it did measure."""

    _score(
        player_stat_specifications.POINTS_MODEL,
        **{evaluation.EXPECTED_VALUE_MAE: 4.33, evaluation.ACCURACY: 0.147}
    )

    scored = model_evaluation("player_stats", "points")

    assert scored is not None
    assert [metric.key for metric in scored.metrics] == [
        evaluation.EXPECTED_VALUE_MAE,
        evaluation.ACCURACY
    ]
    assert scored.metrics[0].floor == 5.5
    assert scored.metrics[1].floor is None
    assert scored.metrics[0].label and scored.metrics[0].description


def test_an_unreadable_score_reads_as_no_score_rather_than_failing_the_page():
    file_path = player_stat_specifications.REBOUNDS_MODEL.evaluation_file()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("{ not json", encoding="utf-8")

    assert model_evaluation("player_stats", "rebounds") is None
