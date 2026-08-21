from datetime import date, datetime, timedelta

from fastapi import HTTPException

from nba_ml import season
from nba_ml.api.app import (
    ACTIVE_TEAM_WINDOW,
    all_models,
    all_teams,
    family_info_models,
    game_rosters,
    model_evaluation
)
from nba_ml.api.schemas import GameRequest, GameRostersRequest, ScenarioRequest
from nba_ml.entities import Game, GameStatus, ScheduledGame
from nba_ml.machine_learning import evaluation
from nba_ml.models import metrics
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.stores import player_games, players, rosters, schedule, team_games, teams

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


def test_every_model_is_named_and_explained_wherever_it_is_listed():
    """
    A caller listing models needs the words as well as the shapes, so the catalogue carries both.

    The home page lists every family and the models in each, from the one catalogue request the site
    already makes. Asking the Info endpoint per family instead would be three more requests for two
    fields the catalogue could have carried. The Info endpoint stays, narrowed to exactly what a card
    reads, because that page reads nothing else.
    """

    catalogue = [model.model_dump() for model in all_models()]
    info_models = [model.model_dump() for model in family_info_models("player_stats")]

    assert all(model["title"] and model["description"] for model in catalogue)
    assert all(
        {"name", "title", "description", "published"} == model.keys() for model in info_models
    )
    assert len(info_models) == 14


def test_unknown_model_family_has_no_info_catalogue():
    with pytest.raises(HTTPException, match="No model family is named unknown") as raised:
        family_info_models("unknown")

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
    assert any(card.name == "assists" for card in family_info_models("player_stats"))
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


def test_middle_coverage_names_the_value_closest_to_its_goal():
    _score(
        player_stat_specifications.POINTS_MODEL,
        **{evaluation.CENTRAL_INTERVAL_COVERAGE: 0.79}
    )

    scored = model_evaluation("player_stats", "points")

    assert scored is not None
    middle = next(metric for metric in scored.metrics if metric.key == evaluation.CENTRAL_INTERVAL_COVERAGE)
    assert middle.ideal == evaluation.CENTRAL_INTERVAL


def test_an_unreadable_score_reads_as_no_score_rather_than_failing_the_page():
    file_path = player_stat_specifications.REBOUNDS_MODEL.evaluation_file()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("{ not json", encoding="utf-8")

    assert model_evaluation("player_stats", "rebounds") is None


def test_a_game_roster_change_is_keyed_to_the_side_it_belongs_to():
    """
    Both sides of a game can be changed, and getting the two the wrong way round would sit the away
    team's players out for the home team. Nothing else in the request says which side is which.
    """

    teams.store(fake_data.teams_frame())

    home, away = fake_data.TEAMS[0], fake_data.TEAMS[1]
    request = GameRostersRequest(
        home=ScenarioRequest(without=[10, 11]),
        away=ScenarioRequest(returning=[20])
    )
    game = GameRequest(
        date=fake_data.NEXT_GAME_DATE,
        home_team=home.abbreviation,
        away_team=away.abbreviation
    ).to_game()

    scenarios = request.to_scenarios(game)

    assert scenarios[home.id].without == frozenset({10, 11})
    assert scenarios[home.id].returning == frozenset()
    assert scenarios[away.id].returning == frozenset({20})
    assert scenarios[away.id].without == frozenset()


def test_a_side_no_change_was_named_for_plays_whoever_played_its_last_game():
    teams.store(fake_data.teams_frame())

    game = GameRequest(
        date=fake_data.NEXT_GAME_DATE,
        home_team=fake_data.TEAMS[0].abbreviation,
        away_team=fake_data.TEAMS[1].abbreviation
    ).to_game()

    scenarios = GameRostersRequest().to_scenarios(game)

    assert set(scenarios) == set(game.team_ids)
    assert all(not scenario.without and not scenario.returning for scenario in scenarios.values())


def stored_league():
    """A whole fake season, plus one game still to be played between the first two teams."""

    teams.store(fake_data.teams_frame())
    team_games.store(fake_data.team_game_frame())
    player_games.store(fake_data.player_game_frame())
    players.store(fake_data.player_info_frame())

    upcoming = ScheduledGame(
        id=fake_data.game_id(99),
        game=Game(fake_data.NEXT_GAME_DATE, fake_data.TEAMS[0].id, fake_data.TEAMS[1].id),
        status=GameStatus.SCHEDULED
    )
    schedule.store([upcoming])

    return upcoming


def test_a_games_rosters_are_dealt_away_side_first():
    """That is the order a matchup is written in, and the order the board deals its cards."""

    upcoming = stored_league()

    away, home = game_rosters(upcoming.id)

    assert away.team.abbreviation == fake_data.TEAMS[1].abbreviation
    assert home.team.abbreviation == fake_data.TEAMS[0].abbreviation


def test_a_roster_offers_everyone_the_snapshot_puts_on_the_team():
    """
    A player traded since their last game has no game for their new team, so nothing played would
    name them. They are still somebody a reader has to be able to sit out.
    """

    upcoming = stored_league()
    moved = fake_data.player_id(fake_data.TEAMS[1].id, 0)
    rosters.store(fake_data.roster_entries(moved={moved: fake_data.TEAMS[0].id}))

    _, home = game_rosters(upcoming.id)

    assert moved in {player.id for player in home.players}


def on_the_day(monkeypatch):
    """Puts the clock on the upcoming game, so the year of played games behind it is read."""

    monkeypatch.setattr(season, "today", lambda: fake_data.NEXT_GAME_DATE)


def test_a_roster_is_the_played_games_while_no_snapshot_is_held(monkeypatch):
    """Which is what every roster was before any of this was collected."""

    upcoming = stored_league()
    on_the_day(monkeypatch)

    _, home = game_rosters(upcoming.id)

    assert {player.id for player in home.players} == set(
        player_games.player_ids_on_team(fake_data.TEAMS[0].id, date(1970, 1, 1))
    )


def test_a_roster_drops_a_player_the_snapshot_puts_on_another_team(monkeypatch):
    """
    The projected roster, not everyone who has recently played for the team.

    A traded player goes on being what the old team's box scores last said for a whole year, so
    nothing played would take him out of its picker.
    """

    upcoming = stored_league()
    on_the_day(monkeypatch)
    traded = fake_data.player_id(fake_data.TEAMS[1].id, 0)
    rosters.store(fake_data.roster_entries(moved={traded: fake_data.TEAMS[0].id}))

    away, home = game_rosters(upcoming.id)

    assert traded not in {player.id for player in away.players}
    assert traded in {player.id for player in home.players}


def test_a_roster_keeps_a_player_the_snapshot_says_nothing_about(monkeypatch):
    """
    A provider that has simply not listed somebody is not a player who has been dropped.

    So the played games go on placing them, which is the same rule the expected lineup follows.
    """

    upcoming = stored_league()
    on_the_day(monkeypatch)
    unlisted = fake_data.player_id(fake_data.TEAMS[0].id, 0)
    rosters.store(fake_data.roster_entries(left_out={unlisted}))

    _, home = game_rosters(upcoming.id)

    assert unlisted in {player.id for player in home.players}


def test_a_roster_carries_the_lineup_change_the_snapshot_expects():
    upcoming = stored_league()
    hurt = fake_data.player_id(fake_data.TEAMS[0].id, 0)
    rosters.store(fake_data.roster_entries(hurt={hurt}))

    _, home = game_rosters(upcoming.id)

    assert [player.id for player in home.without] == [hurt]
    assert home.returning == []


def test_a_roster_expects_no_change_while_nothing_is_collected():
    """Which is the empty form every prediction was made with before any roster was collected."""

    upcoming = stored_league()

    assert all(not side.without and not side.returning for side in game_rosters(upcoming.id))


def test_a_game_the_schedule_does_not_hold_has_no_rosters():
    teams.store(fake_data.teams_frame())

    with pytest.raises(HTTPException) as refused:
        game_rosters(1234)

    assert refused.value.status_code == 404
