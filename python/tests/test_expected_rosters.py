"""
Turning the collected roster snapshot into the lineup change a prediction is built with.

Every build assumes a team plays whoever played its last game. These are the cases where that is
wrong, and what each of them does to the scenario handed to the build. See nba_ml/expected_rosters.py.
"""

import pytest

from nba_ml import expected_rosters
from nba_ml.data_collection import rosters as roster_collection
from nba_ml.entities import Game, RosterEntry, RosterScenario
from nba_ml.feature_engineering import roster_columns
from nba_ml.stores import player_games, rosters, team_games

import fake_data

BEFORE = fake_data.NEXT_GAME_DATE
TEAM = 1
LAST_LINEUP = {fake_data.player_id(TEAM, number) for number in range(fake_data.PLAYERS_PER_TEAM)}
STAR = fake_data.player_id(TEAM, 0)


def stored_league(player_rows=None):
    """The whole fake season, with the player box scores a test wants to change."""

    team_games.store(fake_data.team_game_frame())
    player_games.store(fake_data.player_game_frame() if player_rows is None else player_rows)


def missing_the_last_game(a_player_id: int):
    """Every player box score except that player's most recent one, so they sat that game out."""

    rows = fake_data.player_game_frame()
    last_game = max(game.id for game in fake_data.games_of(TEAM))
    sat_out = (
        (rows[player_games.PLAYER_ID.category_name] == a_player_id)
        & (rows[player_games.GAME_ID.category_name] == last_game)
    )

    return rows[~sat_out].reset_index(drop=True)


def test_nothing_collected_leaves_every_team_playing_its_last_lineup():
    """This is how every prediction behaved before a roster was ever collected."""

    stored_league()

    assert expected_rosters.expected_scenario(TEAM, BEFORE) == RosterScenario()


def test_the_injury_report_takes_a_player_out_of_the_lineup():
    stored_league()
    rosters.store(fake_data.roster_entries(hurt={STAR}))

    assert expected_rosters.expected_scenario(TEAM, BEFORE).without == {STAR}


def test_a_status_that_is_not_an_absence_leaves_the_player_on_the_floor():
    """Most of an injury report is questionable and probable, and most of those players play."""

    stored_league()
    rosters.store([
        entry if entry.player_id != STAR else RosterEntry(STAR, entry.team_id, "Questionable")
        for entry in fake_data.roster_entries()
    ])

    assert expected_rosters.expected_scenario(TEAM, BEFORE) == RosterScenario()


def test_a_player_who_has_moved_leaves_one_lineup_and_joins_the_other():
    """The trade case, which the two teams read as opposite halves of the same fact."""

    stored_league()
    rosters.store(fake_data.roster_entries(moved={STAR: 2}))

    assert expected_rosters.expected_scenario(TEAM, BEFORE).without == {STAR}
    assert expected_rosters.expected_scenario(2, BEFORE).returning == {STAR}


def test_a_player_the_snapshot_has_never_heard_of_stays_in_the_lineup():
    """
    A service that simply does not list somebody is not a service saying they were dropped.

    Reading a gap as an absence would sit out a player who is about to score thirty, which is a
    louder mistake than leaving the lineup exactly as it was.
    """

    stored_league()
    rosters.store(fake_data.roster_entries(left_out={STAR}))

    assert expected_rosters.expected_scenario(TEAM, BEFORE) == RosterScenario()


def test_a_core_player_who_missed_the_last_game_is_expected_back():
    stored_league(missing_the_last_game(STAR))
    rosters.store(fake_data.roster_entries())

    expected = expected_rosters.expected_scenario(TEAM, BEFORE)

    assert expected.returning == {STAR}
    assert expected.without == set()


def test_a_player_below_the_core_cutoff_is_not_named_at_all():
    """
    The roster columns only ever count core players, so naming anyone else changes nothing.

    It would still fill the reader's field with bench names, which is why the default stops at the
    same cutoff the columns themselves use.
    """

    rows = missing_the_last_game(STAR)
    bench = rows[player_games.PLAYER_ID.category_name] == STAR
    rows.loc[bench, player_games.MINUTES_PLAYED.category_name] = (
        roster_columns.CORE_PLAYER_MINUTES_CUTOFF - 5
    )

    stored_league(rows)
    rosters.store(fake_data.roster_entries())

    assert expected_rosters.expected_scenario(TEAM, BEFORE).returning == set()


def test_both_sides_of_a_game_are_read():
    stored_league()
    rosters.store(fake_data.roster_entries(hurt={STAR}))

    game = Game(BEFORE, TEAM, 2)
    scenarios = expected_rosters.expected_scenarios(game)

    assert set(scenarios) == set(game.team_ids)
    assert scenarios[TEAM].without == {STAR}


def test_a_player_is_never_predicted_out_of_their_own_game():
    """
    A player statistic is about somebody taking the floor, so a default that sits them out is a
    question with no answer. Only the default is corrected: a reader naming somebody out is obeyed.
    """

    expected = RosterScenario.of({STAR}, ())

    assert expected_rosters.with_player_playing(expected, STAR).without == set()
    assert expected_rosters.with_player_playing(expected, STAR + 1) is expected


def test_a_snapshot_is_replaced_rather_than_added_to():
    """A player who has left a roster has to leave this table, not sit in it under an old team."""

    rosters.store(fake_data.roster_entries())
    rosters.store(fake_data.roster_entries(moved={STAR: 2}))

    assert {entry.player_id for entry in rosters.on_team(TEAM)} == LAST_LINEUP - {STAR}
    assert rosters.entries_for([STAR])[STAR].team_id == 2


def test_an_empty_snapshot_is_refused_rather_than_wiping_the_held_one():
    rosters.store(fake_data.roster_entries())

    with pytest.raises(ValueError):
        rosters.store([])

    assert rosters.on_team(TEAM)


def test_a_source_with_no_roster_feed_collects_nothing_and_is_not_a_failure():
    """nba.com publishes none, and an archive collected through it still predicts."""

    assert roster_collection.collect(fake_data.FakeSource(), print_debug=False) == 0
    assert rosters.collected_at() is None


def test_collection_stores_what_the_source_names():
    written = roster_collection.collect(
        fake_data.FakeSource(rosters=fake_data.roster_entries(hurt={STAR})),
        print_debug=False
    )

    assert written == len(fake_data.ALL_PLAYERS)
    assert rosters.collected_at() is not None
    assert not rosters.entries_for([STAR])[STAR].playing
