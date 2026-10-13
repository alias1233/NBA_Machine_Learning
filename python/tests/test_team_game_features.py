"""Tests for the team and game feature build, using games with known values."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from nba_ml import season
from nba_ml.entities import Game, RosterScenario
from nba_ml.feature_engineering import (
    game_columns,
    placeholders,
    roster_columns,
    schedule_columns,
    season_columns,
    team_columns,
    team_game_rows,
    team_rosters
)
from nba_ml.feature_engineering.samples import EvaluationSplit, SplitKey, build_split_samples
from nba_ml.feature_engineering.team_game_rows import TargetValue
from nba_ml.models.game_stats import features as game_stat_features
from nba_ml.models.team_stats import features as team_stat_features
from nba_ml.stores import player_games as player_game_store
from nba_ml.stores import team_games as team_game_store

import fake_data
from fake_data import PlayedGame

FEATURES = team_game_rows.build_feature_set(TargetValue.POINT_DIFFERENTIAL)

BUILD_COLUMNS = {
    "sequence_columns": FEATURES.sequence_columns,
    "static_columns": FEATURES.static_columns
}
"""Column names passed to build_split_samples, which it uses in error messages."""

EVERYTHING_TRAINS = EvaluationSplit(start_date=datetime(2030, 1, 1))
"""A split whose evaluation period starts after the fake league ends, so every game is training data."""

def roster_totals(games=fake_data.SEASON_GAMES, player_rows: pd.DataFrame | None = None):
    """Returns the core roster totals for the given games."""

    return team_rosters.totals_of(
        fake_data.player_game_frame(games) if player_rows is None else player_rows,
        fake_data.team_game_frame(games)
    )

TOTALS = roster_totals()

def built_rows(games=fake_data.SEASON_GAMES) -> pd.DataFrame:
    """Returns the feature rows of the given games, indexed by team and game."""

    rows = team_game_rows.build_rows(
        FEATURES, fake_data.team_game_frame(games), roster_totals(games)
    )

    return rows.set_index([team_game_rows.TEAM_ID, team_game_rows.GAME_ID])

def row_of(rows: pd.DataFrame, team_id: int, game: PlayedGame) -> pd.Series:
    return rows.loc[(team_id, game.id)]

# GAME COLUMNS: #
def test_the_points_on_a_row_are_the_points_that_were_scored():
    rows = built_rows()

    for game in fake_data.SEASON_GAMES:
        assert row_of(rows, game.home_team_id, game)[game_columns.POINTS] == game.home_points
        assert row_of(rows, game.away_team_id, game)[game_columns.POINTS] == game.away_points

def test_a_result_is_read_from_the_row_it_belongs_to():
    game = fake_data.SEASON_GAMES[0]
    rows = built_rows()
    home = row_of(rows, game.home_team_id, game)
    away = row_of(rows, game.away_team_id, game)

    assert home[team_columns.POINT_DIFFERENTIAL] == game.home_points - game.away_points
    assert away[team_columns.POINT_DIFFERENTIAL] == game.away_points - game.home_points
    assert home[team_columns.GAME_TOTAL] == away[team_columns.GAME_TOTAL] == game.home_points + game.away_points
    assert home[team_game_rows.WIN] == 1
    assert home[team_game_rows.WIN_CATEGORY] == team_game_rows.WON
    assert away[team_game_rows.WIN_CATEGORY] == team_game_rows.LOST

def test_home_or_away_is_one_for_away_and_the_home_row_is_marked():
    game = fake_data.SEASON_GAMES[0]
    rows = built_rows()

    assert row_of(rows, game.home_team_id, game)[team_columns.HOME_OR_AWAY] == 0
    assert row_of(rows, game.away_team_id, game)[team_columns.HOME_OR_AWAY] == 1
    assert row_of(rows, game.home_team_id, game)[team_game_rows.IS_HOME_ROW]
    assert not row_of(rows, game.away_team_id, game)[team_game_rows.IS_HOME_ROW]

def test_the_other_side_of_the_game_is_carried_onto_each_row():
    game = fake_data.SEASON_GAMES[0]
    rows = built_rows()
    home = row_of(rows, game.home_team_id, game)

    assert home[team_game_rows.OPPONENT_TEAM_ID] == game.away_team_id
    assert home[team_columns.OPPONENT_PREFIX + game_columns.POINTS] == game.away_points

def test_the_season_phase_is_read_off_the_game_id():
    rows = built_rows()

    assert (rows[season_columns.REGULAR_SEASON] == 1).all()
    assert (rows[season_columns.PLAYOFFS] == 0).all()

# ROLLING AND SCHEDULE COLUMNS: #
def test_a_rolling_column_never_reads_its_own_game():
    rows = built_rows()
    team_id = 1
    played = fake_data.games_of(team_id)
    column = team_game_rows.PAST_MEAN_PREFIX + game_columns.POINTS

    # The first game has no earlier games, and an empty window is filled with 0.
    assert row_of(rows, team_id, played[0])[column] == 0

    for position in range(1, len(played)):
        earlier = [fake_data.points_in(game, team_id) for game in played[:position]]

        assert row_of(rows, team_id, played[position])[column] == pytest.approx(np.mean(earlier))

def test_adding_a_later_game_changes_no_row_in_front_of_it():
    played = list(fake_data.SEASON_GAMES)
    without_the_last = built_rows(played[:-1])
    with_the_last = built_rows(played)

    shared = without_the_last.index

    assert len(shared) == len(with_the_last) - 2

    pd.testing.assert_frame_equal(
        without_the_last.sort_index(),
        with_the_last.loc[shared].sort_index(),
        check_like=True
    )

def test_rest_and_break_length_are_read_off_the_gap_before_a_game():
    rows = built_rows()
    team_id = 2
    played = fake_data.games_of(team_id)

    # Team 2 plays on the 22nd and again on the 23rd, so it has 0 days of rest.
    back_to_back = row_of(rows, team_id, played[1])

    assert back_to_back[schedule_columns.REST] == 0
    assert back_to_back[schedule_columns.BREAK_LENGTH] == pytest.approx(np.log1p(0))
    assert back_to_back[schedule_columns.SEASON_OPENER] == 0

    opener = row_of(rows, team_id, played[0])

    assert opener[schedule_columns.SEASON_OPENER] == 1
    assert opener[schedule_columns.REST] == schedule_columns.MAX_REST

def test_a_win_percentage_never_counts_the_game_it_is_read_on():
    rows = built_rows()
    team_id = 1
    played = fake_data.games_of(team_id)

    # Team 1 wins its first two games and loses the third, so it is 2-1 going into the fourth.
    assert row_of(rows, team_id, played[0])[season_columns.TEAM_WIN_PERCENTAGE] == season_columns.EVEN_RECORD
    assert row_of(rows, team_id, played[0])[season_columns.SEASON_GAME_NUMBER] == 0
    assert row_of(rows, team_id, played[1])[season_columns.TEAM_WIN_PERCENTAGE] == 1.0
    assert row_of(rows, team_id, played[3])[season_columns.TEAM_WIN_PERCENTAGE] == pytest.approx(2 / 3)
    assert row_of(rows, team_id, played[3])[season_columns.SEASON_GAME_NUMBER] == 3

def test_the_season_a_column_of_dates_falls_in_matches_the_season_one_date_falls_in():
    days = [game.day for game in fake_data.SEASON_GAMES]
    column = season_columns.season_of(pd.Series(pd.to_datetime(days)))

    assert list(column) == [season.season_of(day) for day in days]
    assert set(column) == {fake_data.SEASON_YEAR}

# HISTORIES AND SAMPLES: #
def test_a_history_holds_one_team_in_the_order_its_games_were_played():
    histories = team_game_rows.build_histories(FEATURES, fake_data.team_game_frame(), TOTALS)

    assert set(histories) == {team.id for team in fake_data.TEAMS}

    for team_id, history in histories.items():
        played = fake_data.games_of(team_id)

        assert history.game_count == len(played)
        assert list(history.game_ids) == [game.id for game in played]
        assert history.sequence_values.shape == (len(played), len(FEATURES.sequence_columns))
        assert history.static_values.shape == (len(played), len(FEATURES.static_columns))
        assert list(history.outputs) == [
            fake_data.points_in(game, team_id) - fake_data.points_in(game, fake_data.opponent_in(game, team_id))
            for game in played
        ]
        assert list(history.opponent_team_ids) == [fake_data.opponent_in(game, team_id) for game in played]

def test_a_team_statistic_is_one_sample_per_side_and_a_game_statistic_one_per_game():
    games = fake_data.team_game_frame()

    _, (per_side, _, _) = build_split_samples(
        team_game_rows.build_histories(FEATURES, games, TOTALS),
        EVERYTHING_TRAINS,
        team_game_rows.MINIMUM_PAST_GAMES,
        **BUILD_COLUMNS
    )
    _, (per_game, _, _) = build_split_samples(
        team_game_rows.build_histories(
            FEATURES, games, TOTALS, sample_row_column=team_game_rows.IS_HOME_ROW
        ),
        EVERYTHING_TRAINS,
        team_game_rows.MINIMUM_PAST_GAMES,
        read_opponent_history=True,
        **BUILD_COLUMNS
    )

    # Each team's first game has no past games, so it is not a sample.
    sides = 2 * len(fake_data.SEASON_GAMES) - len(fake_data.TEAMS)

    assert len(per_side.outputs) == sides
    assert per_side.sequence_count == 1
    assert per_game.sequence_count == 2

    opened_with = {fake_data.games_of(team.id)[0] for team in fake_data.TEAMS}
    answerable = [game for game in fake_data.SEASON_GAMES if game not in opened_with]

    assert sorted(per_game.outputs) == sorted(
        float(game.home_points - game.away_points) for game in answerable
    )

def test_a_blank_left_in_a_column_stops_training_and_names_the_column():
    histories = team_game_rows.build_histories(FEATURES, fake_data.team_game_frame(), TOTALS)
    blank_column = FEATURES.sequence_columns.index(game_columns.POINTS)

    for history in histories.values():
        history.sequence_values[0, blank_column] = np.nan

    with pytest.raises(ValueError, match=f"{game_columns.POINTS} "):
        build_split_samples(
            histories,
            EVERYTHING_TRAINS,
            team_game_rows.MINIMUM_PAST_GAMES,
            **BUILD_COLUMNS
        )

def test_a_training_era_removes_older_games_from_sequences_and_scaling():
    start = datetime(2024, 10, 30)
    evaluation_starts = datetime(2024, 11, 3)
    histories = team_game_rows.build_histories(FEATURES, fake_data.team_game_frame(), TOTALS)

    sequences, (training, _, _) = build_split_samples(
        histories,
        EvaluationSplit(start_date=evaluation_starts),
        team_game_rows.MINIMUM_PAST_GAMES,
        training_start_date=start,
        **BUILD_COLUMNS
    )

    expected_games = [
        [game for game in fake_data.games_of(team.id) if game.day >= start.date()]
        for team in fake_data.TEAMS
    ]
    assert [len(sequence) for sequence in sequences.sequences] == [
        len(games) for games in expected_games
    ]
    assert list(sequences.training_game_counts) == [
        sum(game.day < evaluation_starts.date() for game in games) for games in expected_games
    ]
    assert (training.sequence_end_indices <= sequences.training_game_counts[training.sequence_indices]).all()

# SPLITS: #
def test_validation_and_test_span_the_same_days_and_share_no_game():
    evaluation_starts = datetime(2024, 10, 25)
    histories = team_game_rows.build_histories(
        FEATURES, fake_data.team_game_frame(), TOTALS, sample_row_column=team_game_rows.IS_HOME_ROW
    )

    _, (training, validation, test) = build_split_samples(
        histories,
        EvaluationSplit(start_date=evaluation_starts, split_on=SplitKey.GAME),
        team_game_rows.MINIMUM_PAST_GAMES,
        read_opponent_history=True,
        **BUILD_COLUMNS
    )

    def days(samples) -> set:
        return set(samples.game_dates.astype("datetime64[D]").tolist())

    assert days(training) and days(validation) and days(test)

    assert max(days(training)) < evaluation_starts.date()
    assert min(days(validation) | days(test)) >= evaluation_starts.date()

    assert min(days(validation)) < max(days(test))
    assert min(days(test)) < max(days(validation))

def test_the_two_evaluation_splits_hold_the_games_of_different_subjects():
    histories = team_game_rows.build_histories(FEATURES, fake_data.team_game_frame(), TOTALS)

    _, (_, validation, test) = build_split_samples(
        histories,
        EvaluationSplit(start_date=datetime(2024, 10, 25), split_on=SplitKey.SUBJECT),
        team_game_rows.MINIMUM_PAST_GAMES,
        **BUILD_COLUMNS
    )

    assert not set(validation.sequence_indices.flatten()) & set(test.sequence_indices.flatten())

def test_the_validation_fraction_decides_which_way_a_whole_split_leans():
    histories = team_game_rows.build_histories(FEATURES, fake_data.team_game_frame(), TOTALS)
    evaluation_starts = datetime(2024, 10, 25)

    def sizes(validation_fraction: float) -> tuple[int, int]:
        _, (_, validation, test) = build_split_samples(
            histories,
            EvaluationSplit(
                start_date=evaluation_starts,
                validation_fraction=validation_fraction,
                split_on=SplitKey.GAME
            ),
            team_game_rows.MINIMUM_PAST_GAMES,
            **BUILD_COLUMNS
        )

        return (len(validation.outputs), len(test.outputs))

    assert sizes(1.0)[1] == 0
    assert sizes(0.0)[0] == 0
    assert sum(sizes(0.5)) == sum(sizes(1.0))

def test_a_validation_fraction_outside_a_share_is_refused():
    with pytest.raises(ValueError, match="validation fraction"):
        EvaluationSplit(start_date=datetime(2024, 10, 25), validation_fraction=1.5)

# CORE ROSTERS: #
def _roster_column(prefix: str) -> str:
    """Returns the core roster minutes column for the given prefix."""

    return prefix + team_rosters.PAST_MEAN_PREFIX + fake_data.player_games.MINUTES_PLAYED.category_name

def test_a_row_totals_what_the_core_players_a_team_is_missing_were_averaging():
    team_id = 1
    played = fake_data.games_of(team_id)
    star = fake_data.player_id(team_id, 0)
    last_game = played[-1]

    player_rows = fake_data.player_game_frame()
    sat_out = (
        (player_rows[fake_data.player_games.PLAYER_ID.category_name] == star)
        & (player_rows[fake_data.player_games.GAME_ID.category_name] == last_game.id)
    )
    rows = team_game_rows.build_rows(
        FEATURES,
        fake_data.team_game_frame(),
        roster_totals(player_rows=player_rows[~sat_out])
    ).set_index([team_game_rows.TEAM_ID, team_game_rows.GAME_ID])

    lost = _roster_column(roster_columns.LOST_CORE_TEAMMATE_PREFIX)
    absent = _roster_column(roster_columns.ABSENT_CORE_TEAMMATE_PREFIX)

    # Every player averages 30 minutes in the fake league, so the team lost 30.
    assert row_of(rows, team_id, last_game)[lost] == pytest.approx(30)
    assert row_of(rows, team_id, last_game)[absent] > 0

    # Nobody had missed a game before that one.
    assert row_of(rows, team_id, played[-2])[lost] == 0
    assert row_of(rows, team_id, played[-2])[absent] == 0

    # The opponent's row has the same value in its opponent column.
    opponent_id = fake_data.opponent_in(last_game, team_id)

    assert row_of(rows, opponent_id, last_game)[team_columns.OPPONENT_PREFIX + lost] == pytest.approx(30)

# INFERENCE: #
def test_a_prediction_reads_the_home_team_first_and_only_the_games_before_the_one_asked_about():
    team_game_store.store(fake_data.team_game_frame())
    player_game_store.store(fake_data.player_game_frame())

    features = game_stat_features.build_feature_set(TargetValue.POINT_DIFFERENTIAL)
    target = Game(fake_data.NEXT_GAME_DATE, home_team_id=1, away_team_id=2)

    sequences, sample = game_stat_features.get_inference_data(features, target, {})

    assert len(sequences.sequences) == 2
    assert list(sample.sequence_end_indices[0]) == [len(fake_data.games_of(1)), len(fake_data.games_of(2))]
    assert list(sample.opponent_team_ids[0]) == [2, 1]
    assert sample.static_inputs.shape == (1, len(features.static_columns))

    # HOME_OR_AWAY is not a static column for game models, since every sample is a home row.
    assert team_columns.HOME_OR_AWAY not in features.static_columns
    assert team_columns.HOME_OR_AWAY in features.sequence_columns

def test_the_placeholder_row_of_a_game_not_yet_played_is_built_from_the_games_behind_it():
    target = Game(fake_data.NEXT_GAME_DATE, home_team_id=1, away_team_id=2)
    with_placeholder = pd.concat(
        [fake_data.team_game_frame(), placeholders.game_rows(target)],
        ignore_index=True
    )

    histories = team_game_rows.build_histories(FEATURES, with_placeholder, TOTALS)
    found = team_game_rows.find_target_game(histories, 1, target)

    assert found is not None

    history, index = found
    played = fake_data.games_of(1)

    assert index == len(played)

    column = FEATURES.static_columns.index(team_game_rows.PAST_MEAN_PREFIX + game_columns.POINTS)
    scored = [fake_data.points_in(game, 1) for game in played[-team_game_rows.ROLLING_WINDOW:]]

    assert history.static_values[index][column] == pytest.approx(np.mean(scored))

def test_naming_a_side_without_a_core_player_changes_the_predicted_game_and_nothing_behind_it():
    team_game_store.store(fake_data.team_game_frame())
    player_game_store.store(fake_data.player_game_frame())

    features = game_stat_features.build_feature_set(TargetValue.POINT_DIFFERENTIAL)
    target = Game(fake_data.NEXT_GAME_DATE, home_team_id=1, away_team_id=2)
    away_star = fake_data.player_id(2, 0)

    everyone_sequences, everyone = game_stat_features.get_inference_data(features, target, {})
    without_sequences, without = game_stat_features.get_inference_data(
        features, target, {2: RosterScenario.of(without=[away_star])}
    )

    for side in range(len(everyone_sequences.sequences)):
        np.testing.assert_array_equal(
            without_sequences.sequences[side],
            everyone_sequences.sequences[side]
        )

    assert not np.array_equal(without.static_inputs, everyone.static_inputs)

def test_a_team_statistic_reads_the_roster_of_both_sides():
    team_game_store.store(fake_data.team_game_frame())
    player_game_store.store(fake_data.player_game_frame())

    features = team_stat_features.build_feature_set(TargetValue.TEAM_POINTS)
    target = Game(fake_data.NEXT_GAME_DATE, home_team_id=1, away_team_id=2)
    named, facing = 1, 2

    _, everyone = team_stat_features.get_inference_data(features, named, target, {})

    for team_id in (named, facing):
        _, without = team_stat_features.get_inference_data(
            features,
            named,
            target,
            {team_id: RosterScenario.of(without=[fake_data.player_id(team_id, 0)])}
        )

        assert not np.array_equal(without.static_inputs, everyone.static_inputs)

def test_naming_a_player_as_joining_moves_the_predicted_game_too():
    team_game_store.store(fake_data.team_game_frame())
    player_game_store.store(fake_data.player_game_frame())

    features = game_stat_features.build_feature_set(TargetValue.POINT_DIFFERENTIAL)
    target = Game(fake_data.NEXT_GAME_DATE, home_team_id=1, away_team_id=2)

    # A player from a team outside this game, which is how a newly signed player looks to the build.
    joining = fake_data.player_id(3, 0)

    _, everyone = game_stat_features.get_inference_data(features, target, {})
    _, joined = game_stat_features.get_inference_data(
        features, target, {1: RosterScenario.of(returning=[joining])}
    )

    assert not np.array_equal(joined.static_inputs, everyone.static_inputs)

def test_a_team_with_nothing_behind_the_predicted_game_cannot_be_answered_for():
    first_game = fake_data.SEASON_GAMES[0]
    target = Game(date=first_game.day - timedelta(days=1), home_team_id=1, away_team_id=2)
    with_placeholder = pd.concat(
        [fake_data.team_game_frame([first_game]), placeholders.game_rows(target)],
        ignore_index=True
    )

    histories = team_game_rows.build_histories(
        FEATURES, with_placeholder, roster_totals([first_game])
    )

    assert team_game_rows.find_target_game(histories, 1, target) is None
