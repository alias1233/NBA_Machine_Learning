"""Compatibility with game rows collected before season phase was stored explicitly."""

from nba_ml.entities import Game, RosterScenario
from nba_ml.models.player_stats import features as player_features
from nba_ml.models.player_stats import specifications as player_specifications
from nba_ml.models.team_stats import features as team_features
from nba_ml.models.team_stats import specifications as team_specifications
from nba_ml.stores import player_games, players, team_games

import fake_data


def test_legacy_nba_api_rows_can_build_prediction_histories():
    team_rows = fake_data.team_game_frame()
    player_rows = fake_data.player_game_frame()
    team_rows[team_games.SEASON_TYPE.category_name] = None
    player_rows[player_games.SEASON_TYPE.category_name] = None

    team_games.store(team_rows)
    player_games.store(player_rows)
    players.store(fake_data.player_info_frame())

    target_game = Game(fake_data.NEXT_GAME_DATE, 1, 2)
    team_specification = team_specifications.ALL_MODEL_SPECIFICATIONS["team_points"]
    _, team_sample = team_features.get_inference_data(
        team_specification.get_feature_set(),
        target_game.home_team_id,
        target_game,
        {}
    )
    player_id = fake_data.player_id(target_game.home_team_id, 0)
    player_specification = player_specifications.ALL_MODEL_SPECIFICATIONS["points"]
    _, player_sample = player_features.get_inference_data(
        player_specification.get_feature_set(),
        player_id,
        target_game.home_team_id,
        target_game,
        RosterScenario()
    )

    assert team_sample.sequence_end_indices[0].tolist() == [6, 6]
    assert player_sample.sequence_end_indices[0].tolist() == [6]
