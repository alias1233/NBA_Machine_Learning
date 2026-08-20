"""
Filling the seasons in front of the data source's floor from an older archive.

Both archives here hold the same made up league, and every identifier in the older one differs.
Working out which player is which without being told is the whole job, so most of what follows
checks that a career reads as one career afterwards and that nothing collides.

The cutoff is moved into the middle of the fake season, so games before 2024-10-30 stand for the
seasons only the older archive reaches and the six games from it onwards stand for the overlap the
matching is done in. See nba_ml/data_collection/legacy_archive.py.
"""

from datetime import date

import pandas as pd
import pytest

from nba_ml.data_collection import games, legacy_archive
from nba_ml.entities import Game, RosterScenario
from nba_ml.models.player_stats import features as player_features
from nba_ml.models.player_stats import specifications as player_specifications
from nba_ml.season import SeasonType
from nba_ml.stores import player_games, players, team_games, teams

import fake_data

CUTOFF = date(2024, 10, 30)
"""Stands for the first date the data source itself covers."""

OLDER_GAMES = tuple(game for game in fake_data.SEASON_GAMES if game.day < CUTOFF)
SHARED_GAMES = tuple(game for game in fake_data.SEASON_GAMES if game.day >= CUTOFF)

RETIRED = frozenset(
    player.id for player in fake_data.ALL_PLAYERS if player.id % 100 == fake_data.PLAYERS_PER_TEAM - 1
)
"""
Whose place in the older era was held by somebody else.

Each team's last place belonged to a player who had stopped playing by the cutoff, so four players
exist only in the older archive and nothing after it names them. Everybody else played both eras.
"""


def legacy_rows(older=OLDER_GAMES, shared=SHARED_GAMES) -> pd.DataFrame:
    """Everything the older archive holds: its own era under its own ids, then the shared games."""

    return pd.concat(
        [
            fake_data.legacy_player_game_frame(older, retired=RETIRED),
            fake_data.legacy_player_game_frame(shared)
        ],
        ignore_index=True
    )


def collected_archive():
    """What the data source itself has collected, which is only the games from the cutoff on."""

    teams.store(fake_data.teams_frame())
    players.store(fake_data.player_info_frame())
    player_games.store(fake_data.player_game_frame(SHARED_GAMES))
    games.collect_team_games(print_debug=False)


def imported(rows: pd.DataFrame | None = None, **arguments) -> legacy_archive.ImportReport:
    collected_archive()
    directory = fake_data.write_legacy_archive(
        fake_data.Path(str(player_games.FILEPATH.parent.parent / "legacy")),
        legacy_rows() if rows is None else rows
    )

    return legacy_archive.import_games(directory, until=CUTOFF, print_debug=False, **arguments)


# WHO IS WHO: #
def test_a_player_is_recognised_by_the_games_both_archives_hold():
    """
    The point of the whole command. A player who was already collected keeps the identifier they
    were collected under, so the games in front of the cutoff join onto the career they belong to.
    """

    report = imported()

    stored = player_games.get_all_player_game_data()
    joined = fake_data.ALL_PLAYERS[0]
    theirs = stored[stored[player_games.PLAYER_ID.category_name] == joined.id]

    assert report.joined_players == len(fake_data.ALL_PLAYERS)
    assert report.unjoined_players == ()
    assert len(theirs) == len(fake_data.games_of(fake_data.team_of(joined.id)))
    assert theirs[player_games.GAME_DATE.category_name].min() == "2024-10-22"


def test_a_player_of_the_older_era_only_is_given_an_identifier_of_their_own():
    report = imported()

    stored = set(player_games.get_all_player_game_data()[player_games.PLAYER_ID.category_name])
    made_up = {player_id for player_id in stored if player_id >= legacy_archive.LEGACY_PLAYER_ID_BASE}

    assert report.legacy_only_players == len(RETIRED)
    assert len(made_up) == len(RETIRED)
    assert made_up.isdisjoint(player.id for player in fake_data.ALL_PLAYERS)


def test_two_legacy_players_never_collapse_onto_one_identifier():
    report = imported()

    stored = player_games.get_all_player_game_data()
    one_team_one_game = stored[
        stored[player_games.GAME_ID.category_name] == stored[player_games.GAME_ID.category_name].min()
    ]

    assert report.players_without_information == ()
    assert not one_team_one_game[player_games.PLAYER_ID.category_name].duplicated().any()


def test_a_player_seen_in_too_few_shared_games_is_named_as_a_career_split_in_two():
    """
    Three agreeing games is the floor, and each player here plays exactly three shared games. Ask
    for more and nobody is recognised, which the report has to say plainly rather than swallow.
    """

    report = imported(minimum_matching_games=len(SHARED_GAMES))

    assert report.joined_players == 0
    assert len(report.unjoined_players) == len(fake_data.ALL_PLAYERS) - len(RETIRED)
    assert "reads as two careers" in report.describe()


def test_an_import_is_refused_before_anything_is_collected_from_the_source():
    directory = fake_data.write_legacy_archive(
        fake_data.Path(str(player_games.FILEPATH.parent.parent / "legacy")), legacy_rows()
    )

    with pytest.raises(RuntimeError, match="Collect from the data source first"):
        legacy_archive.import_games(directory, until=CUTOFF, print_debug=False)


# WHAT IS WRITTEN: #
def test_only_the_games_in_front_of_the_cutoff_are_imported():
    report = imported()

    stored = player_games.get_all_player_game_data()
    made_up = stored[player_games.GAME_ID.category_name] >= legacy_archive.LEGACY_GAME_ID_BASE

    assert report.games == len(OLDER_GAMES)
    assert set(stored.loc[made_up, player_games.GAME_DATE.category_name]) == {
        "2024-10-22", "2024-10-23", "2024-10-25", "2024-10-27"
    }
    assert stored.loc[~made_up, player_games.GAME_DATE.category_name].min() == "2024-10-30"


def test_an_imported_game_is_given_an_identifier_no_provider_answers_to():
    imported()

    stored = player_games.get_all_player_game_data()
    older = stored[stored[player_games.GAME_DATE.category_name] < "2024-10-30"]

    assert (older[player_games.GAME_ID.category_name] >= legacy_archive.LEGACY_GAME_ID_BASE).all()
    assert older[player_games.GAME_ID.category_name].nunique() == len(OLDER_GAMES)


def test_team_ids_are_matched_on_the_tricode_both_services_publish():
    report = imported()

    stored = player_games.get_all_player_game_data()

    assert report.unmapped_teams == ()
    assert set(stored[player_games.TEAM_ID.category_name]) == {team.id for team in fake_data.TEAMS}


def test_a_team_that_matches_nothing_takes_its_games_with_it():
    rows = legacy_rows()
    overseas = rows[player_games.GAME_ID.category_name] == rows[player_games.GAME_ID.category_name].min()
    rows.loc[overseas, player_games.TEAM_ID.category_name] = 99_999

    report = imported(rows)

    assert 99_999 in report.unmapped_teams
    assert report.games == len(OLDER_GAMES) - 1


def test_team_rows_are_rebuilt_from_the_imported_player_rows():
    report = imported()

    stored = team_games.get_all_team_game_data()
    older = stored[stored[team_games.GAME_DATE.category_name] < "2024-10-30"]
    first = older.iloc[0]
    behind_it = player_games.get_all_player_game_data()
    behind_it = behind_it[
        (behind_it[player_games.TEAM_ID.category_name] == first[team_games.TEAM_ID.category_name])
        & (behind_it[player_games.GAME_ID.category_name] == first[team_games.GAME_ID.category_name])
    ]

    assert report.team_rows == len(OLDER_GAMES) * 2
    assert first[team_games.FIELD_GOALS_MADE.category_name] == behind_it[
        player_games.FIELD_GOALS_MADE.category_name
    ].sum()


def test_importing_twice_leaves_the_same_archive():
    first = imported()
    rows = len(player_games.get_all_player_game_data())

    second = legacy_archive.import_games(
        fake_data.Path(str(player_games.FILEPATH.parent.parent / "legacy")),
        until=CUTOFF,
        print_debug=False
    )

    assert (second.games, second.player_rows) == (first.games, first.player_rows)
    assert len(player_games.get_all_player_game_data()) == rows


# WHAT IS LEFT OUT: #
def test_preseason_is_left_out_and_play_in_is_filed_as_the_regular_season():
    play_in, preseason = OLDER_GAMES[:1], OLDER_GAMES[1:2]
    rows = pd.concat(
        [
            fake_data.legacy_player_game_frame(play_in, RETIRED, SeasonType.PLAY_IN),
            fake_data.legacy_player_game_frame(preseason, RETIRED, SeasonType.PRESEASON),
            fake_data.legacy_player_game_frame(OLDER_GAMES[2:], retired=RETIRED),
            fake_data.legacy_player_game_frame(SHARED_GAMES)
        ],
        ignore_index=True
    )

    report = imported(rows)

    stored = player_games.get_all_player_game_data()
    phases = set(stored.loc[
        stored[player_games.GAME_ID.category_name] >= legacy_archive.LEGACY_GAME_ID_BASE,
        player_games.SEASON_TYPE.category_name
    ])

    assert report.games == len(OLDER_GAMES) - 1
    assert report.skipped_games == 1
    assert phases == {legacy_archive.IMPORTED_PHASES[
        legacy_archive.season.GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON]
    ]}


def test_a_game_missing_one_of_its_stats_is_left_out_whole():
    rows = legacy_rows()
    oldest = rows[player_games.GAME_ID.category_name] == rows[player_games.GAME_ID.category_name].min()
    rows.loc[rows[oldest].index[0], player_games.PLUS_MINUS.category_name] = None

    report = imported(rows)

    assert report.games == len(OLDER_GAMES) - 1
    assert report.skipped_games == 1


def test_a_game_only_one_team_played_is_left_out():
    rows = legacy_rows()
    oldest = rows[player_games.GAME_ID.category_name].min()
    one_side = (rows[player_games.GAME_ID.category_name] == oldest) & (
        rows[player_games.TEAM_ID.category_name] == fake_data.LEGACY_TEAM_IDS[1]
    )

    report = imported(rows[~one_side].reset_index(drop=True))

    assert report.games == len(OLDER_GAMES) - 1


def test_a_player_who_did_not_appear_does_not_reject_the_game_around_them():
    rows = legacy_rows()
    absent = rows.index[0]
    rows.loc[absent, player_games.MINUTES_PLAYED.category_name] = 0

    report = imported(rows)

    stored = player_games.get_all_player_game_data()
    game_ids = stored[player_games.GAME_ID.category_name]
    oldest = game_ids[game_ids >= legacy_archive.LEGACY_GAME_ID_BASE].min()

    assert report.games == len(OLDER_GAMES)
    assert (game_ids == oldest).sum() == fake_data.PLAYERS_PER_TEAM * 2 - 1


# WHAT COMES AFTER: #
def test_the_information_of_a_player_of_the_older_era_is_imported():
    """A build drops every game of a player it knows nothing about, so these rows have to arrive."""

    report = imported()

    described = players.stored_player_ids()
    made_up = {player_id for player_id in described if player_id >= legacy_archive.LEGACY_PLAYER_ID_BASE}

    assert report.player_info_rows == len(RETIRED)
    assert len(made_up) == len(RETIRED)
    assert report.players_without_information == ()


def test_career_years_are_reread_from_the_archive_the_import_leaves_behind():
    """
    The provider publishes no debut year, so collection reads one off a player's own games. Filling
    the archive with older seasons moves it, and every held player has to be told.
    """

    players.store(fake_data.player_info_frame().assign(FROM_YEAR=None, TO_YEAR=None))
    imported()

    described = players.get_all_players_info()
    joined = described[described[players.PLAYER_ID.category_name] == fake_data.ALL_PLAYERS[0].id].iloc[0]

    assert joined[players.FROM_YEAR.category_name] == fake_data.SEASON_YEAR
    assert joined[players.TO_YEAR.category_name] == fake_data.SEASON_YEAR


def test_an_imported_game_is_read_as_part_of_the_career_it_belongs_to():
    """What the import is for. A sequence now reaches back past the date the provider starts at."""

    imported()
    team_id = fake_data.TEAMS[0].id
    player = fake_data.ALL_PLAYERS[0]
    specification = player_specifications.ALL_MODEL_SPECIFICATIONS["points"]

    _, sample = player_features.get_inference_data(
        specification.get_feature_set(),
        player.id,
        team_id,
        Game(fake_data.NEXT_GAME_DATE, team_id, fake_data.TEAMS[1].id),
        RosterScenario()
    )

    assert sample.sequence_end_indices[0].tolist() == [len(fake_data.games_of(team_id))]
