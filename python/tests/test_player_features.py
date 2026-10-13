"""Tests for the player stats feature build and inference inputs."""

import numpy as np
import pytest

from nba_ml.entities import Game, RosterScenario
from nba_ml.feature_engineering import feature_store, game_columns, player_columns
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.models.player_stats import features, specifications
from nba_ml.stores import player_games, players, team_games

import fake_data

POINTS_MODEL = specifications.ALL_MODEL_SPECIFICATIONS["points"]

TARGET_PLAYER_ID = fake_data.player_id(1, 0)
"""The first player of team 1, who scores the most points on their team."""

TARGET_TEAM_ID = fake_data.team_of(TARGET_PLAYER_ID)

@pytest.fixture
def collected_league():
    """Stores the full fake league, as a collection run would."""

    players.store(fake_data.player_info_frame())
    player_games.store(fake_data.player_game_frame())
    team_games.store(fake_data.team_game_frame())

@pytest.fixture
def features_read():
    """Returns the feature set of the points model."""

    return POINTS_MODEL.get_feature_set()

def target_game(home_team_id: int = TARGET_TEAM_ID, away_team_id: int = 2) -> Game:
    return Game(fake_data.NEXT_GAME_DATE, home_team_id, away_team_id)

def publish_league_build():
    """Builds and publishes a feature build from the stored data."""

    union = specifications.union_feature_set()

    return feature_store.publish(
        features.BUILD_NAME,
        feature_store.from_histories(
            features.build_league_histories(union),
            union.sequence_columns,
            None
        )
    )

# LEAGUE BUILD: #
def test_the_league_build_holds_every_player_and_every_game_they_played(collected_league, features_read):
    histories = features.build_league_histories(features_read)

    assert set(histories) == {player.id for player in fake_data.ALL_PLAYERS}

    for player_id, history in histories.items():
        played = fake_data.games_of(fake_data.team_of(player_id))

        assert history.game_count == len(played)
        assert list(history.game_ids) == [game.id for game in played]

def test_a_player_without_a_birthdate_remains_in_the_build(collected_league, features_read):
    player_info = players.get_all_players_info()
    player_info[players.BIRTHDATE.category_name] = None
    players.store(player_info)

    histories = features.build_league_histories(features_read)

    assert set(histories) == {player.id for player in fake_data.ALL_PLAYERS}

def test_a_player_with_no_draft_record_reads_as_undrafted_rather_than_as_a_blank(
    collected_league,
    features_read
    ):
    written = fake_data.player_info_frame()
    written[players.DRAFT_NUMBER.category_name] = None
    players.store(written)

    read = player_columns.encode_undrafted(
        players.get_all_players_info(),
        players.DRAFT_NUMBER.category_name
    )

    assert (read[player_columns.UNDRAFTED] == 1).all()
    assert (read[players.DRAFT_NUMBER.category_name] == 0).all()

    histories = features.build_league_histories(features_read)

    assert np.isfinite([history.static_subject_values for history in histories.values()]).all()

def test_an_empty_player_store_explains_that_training_needs_collection(features_read):
    with pytest.raises(ValueError, match="No usable player information is stored"):
        features.build_league_histories(features_read)

def test_a_players_own_scoring_and_plus_minus_reach_the_build_as_recorded(collected_league, features_read):
    history = features.build_league_histories(features_read)[TARGET_PLAYER_ID]
    points_column = features_read.sequence_columns.index(game_columns.POINTS + player_columns.PLAYER_SUFFIX)
    plus_minus_column = features_read.sequence_columns.index(player_games.PLUS_MINUS.category_name)

    for position, game in enumerate(fake_data.games_of(TARGET_TEAM_ID)):
        scored = fake_data.player_points(
            TARGET_PLAYER_ID,
            fake_data.points_in(game, TARGET_TEAM_ID)
        )
        plus_minus = fake_data.points_in(game, TARGET_TEAM_ID) - fake_data.points_in(
            game, fake_data.opponent_in(game, TARGET_TEAM_ID)
        )

        assert history.sequence_values[position][points_column] == pytest.approx(scored)
        assert history.sequence_values[position][plus_minus_column] == pytest.approx(plus_minus)

def test_one_build_covers_every_model_of_the_family(collected_league, features_read):
    union = specifications.union_feature_set()
    build = feature_store.from_histories(
        features.build_league_histories(union),
        union.sequence_columns,
        None
    )

    positions = build.column_positions(features_read.sequence_columns)

    assert len(positions) == len(features_read.sequence_columns)
    assert build.game_count == len(fake_data.ALL_PLAYERS) * len(fake_data.games_of(TARGET_TEAM_ID))

# INFERENCE: #
def test_a_prediction_reads_every_game_played_before_the_one_asked_about(collected_league, features_read):
    sequences, sample = features.get_inference_data(
        features_read,
        TARGET_PLAYER_ID,
        TARGET_TEAM_ID,
        target_game(),
        RosterScenario()
    )

    history = features.build_league_histories(features_read)[TARGET_PLAYER_ID]
    played = len(fake_data.games_of(TARGET_TEAM_ID))

    assert len(sequences.sequences) == 1
    assert sequences.sequences[0].shape == (played, len(features_read.sequence_columns))
    assert list(sample.sequence_end_indices[0]) == [played]
    assert sample.opponent_team_ids[0][0] == 2

    # The static input is the player info features followed by the target game's static columns.
    assert sample.static_inputs.shape == (1, len(history.static_input(0)))

def test_a_published_build_answers_a_prediction_exactly_as_building_the_league_per_request_does(
    collected_league,
    features_read
    ):
    arguments = (features_read, TARGET_PLAYER_ID, TARGET_TEAM_ID, target_game(), RosterScenario())

    per_request_sequences, per_request_sample = features.get_inference_data(*arguments)

    publish_league_build()

    assert feature_store.current(features.BUILD_NAME) is not None

    published_sequences, published_sample = features.get_inference_data(*arguments)

    np.testing.assert_array_equal(published_sequences.sequences[0], per_request_sequences.sequences[0])
    np.testing.assert_array_equal(published_sample.static_inputs, per_request_sample.static_inputs)

def test_taking_a_core_teammate_out_changes_the_predicted_game_and_nothing_behind_it(
    collected_league,
    features_read
    ):
    teammate = fake_data.player_id(TARGET_TEAM_ID, 1)
    arguments = (features_read, TARGET_PLAYER_ID, TARGET_TEAM_ID, target_game())

    with_everyone_sequences, with_everyone = features.get_inference_data(
        *arguments, RosterScenario()
    )
    without_teammate_sequences, without_teammate = features.get_inference_data(
        *arguments, RosterScenario.of(without=[teammate])
    )

    np.testing.assert_array_equal(
        without_teammate_sequences.sequences[0],
        with_everyone_sequences.sequences[0]
    )
    assert not np.array_equal(without_teammate.static_inputs, with_everyone.static_inputs)

# REFUSED REQUESTS: #
def test_a_player_nothing_is_stored_about_is_refused_rather_than_answered(collected_league, features_read):
    unknown_player_id = 9999

    with pytest.raises(PredictionRefused) as refused:
        features.get_inference_data(
            features_read, unknown_player_id, TARGET_TEAM_ID, target_game(), RosterScenario()
        )

    assert refused.value.reason is Refusal.MISSING_PLAYER_INFORMATION

def test_a_team_with_no_game_before_the_predicted_one_is_refused(features_read):
    first_game = fake_data.SEASON_GAMES[0]

    players.store(fake_data.player_info_frame())
    player_games.store(fake_data.player_game_frame([first_game]))
    team_games.store(fake_data.team_game_frame([first_game]))

    with pytest.raises(PredictionRefused) as refused:
        features.get_inference_data(
            features_read,
            TARGET_PLAYER_ID,
            TARGET_TEAM_ID,
            Game(first_game.day, TARGET_TEAM_ID, 2),
            RosterScenario()
        )

    assert refused.value.reason is Refusal.NO_TEAM_HISTORY
