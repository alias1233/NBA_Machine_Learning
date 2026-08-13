"""
The checks every family makes on a request before it builds anything.

A game already played is the one worth pinning down. Asking for it looks like an ordinary request and
answers like one, because the build stands the game in as a placeholder row that sits behind the real
game the sequence stops in front of. The two halves of the answer then describe different histories,
and nothing says so.
"""

import pytest

from nba_ml.entities import Game
from nba_ml.models import requests
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.models.player_stats import inference as player_stat_inference
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.stores import player_games, players, team_games

import fake_data

PLAYED_GAME = fake_data.SEASON_GAMES[0]

@pytest.fixture(autouse=True)
def collected_league():
    players.store(fake_data.player_info_frame())
    player_games.store(fake_data.player_game_frame())
    team_games.store(fake_data.team_game_frame())

def test_a_game_still_to_be_played_is_allowed():
    requests.refuse_a_played_game(Game(fake_data.NEXT_GAME_DATE, 1, 2))

def test_a_game_already_collected_is_refused():
    with pytest.raises(PredictionRefused) as refused:
        requests.refuse_a_played_game(
            Game(PLAYED_GAME.day, PLAYED_GAME.home_team_id, PLAYED_GAME.away_team_id)
        )

    assert refused.value.reason is Refusal.GAME_ALREADY_PLAYED

def test_one_team_having_played_that_day_is_enough_to_refuse():
    """No team plays twice in a day, so a stored game is the game being asked about."""

    # The one day the fake league does not fill: teams 2 and 3 play, teams 1 and 4 rest.
    day = fake_data.SEASON_GAMES[2].day
    played_that_day = {
        team_id for game in fake_data.SEASON_GAMES if game.day == day for team_id in
        (game.home_team_id, game.away_team_id)
    }
    resting_team_id = next(team.id for team in fake_data.TEAMS if team.id not in played_that_day)

    with pytest.raises(PredictionRefused) as refused:
        requests.refuse_a_played_game(Game(day, min(played_that_day), resting_team_id))

    assert refused.value.reason is Refusal.GAME_ALREADY_PLAYED

def test_a_prediction_refuses_a_played_game_before_it_reads_a_model():
    """
    Checked on the real inference path, which no model file exists for here. Reaching the refusal
    rather than a missing file is what says the check runs first.
    """

    with pytest.raises(PredictionRefused) as refused:
        player_stat_inference.predict(
            player_stat_specifications.ALL_MODEL_SPECIFICATIONS["points"],
            fake_data.player_id(PLAYED_GAME.home_team_id, 0),
            Game(PLAYED_GAME.day, PLAYED_GAME.home_team_id, PLAYED_GAME.away_team_id),
            print_debug=False
        )

    assert refused.value.reason is Refusal.GAME_ALREADY_PLAYED
