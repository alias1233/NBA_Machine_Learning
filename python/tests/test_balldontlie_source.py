"""BALLDONTLIE's ALL-STAR contract, without network access."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import requests

from nba_ml import paths, sources
from nba_ml.data_collection import source_identity
from nba_ml.entities import GameStatus
from nba_ml.feature_engineering import season_columns
from nba_ml.season import GAME_ID_PREFIXES, SeasonType
from nba_ml.sources import balldontlie_source
from nba_ml.sources.balldontlie_source import BallDontLieSource
from nba_ml.sources.base import SourceAuthenticationError, SourceDataError
from nba_ml.sources import nba_api_source
from nba_ml.sources.nba_api_source import NBAApiSource


class Response:
    def __init__(self, payload, status=200, headers=None):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


TEAMS = [
    {"id": 1, "full_name": "Atlanta Hawks", "abbreviation": "ATL"},
    {"id": 2, "full_name": "Boston Celtics", "abbreviation": "BOS"}
]


def stat(player_id, team_id, minutes, fgm, turnovers, plus_minus):
    return {
        "player": {"id": player_id},
        "team": {"id": team_id, "abbreviation": TEAMS[team_id - 1]["abbreviation"]},
        "game": {
            "id": 18400001,
            "date": "2024-10-22",
            "season": 2024,
            "status": "Final",
            "postseason": False,
            "home_team_id": 1,
            "visitor_team_id": 2,
            "home_team_score": 110,
            "visitor_team_score": 100
        },
        "min": minutes,
        "fgm": fgm,
        "fga": fgm + 3,
        "fg3m": 1,
        "fg3a": 2,
        "ftm": 2,
        "fta": 2,
        "oreb": 1,
        "dreb": 3,
        "ast": 4,
        "stl": 1,
        "blk": 0,
        "turnover": turnovers,
        "pf": 2,
        "plus_minus": plus_minus
    }


def test_stats_are_paginated_and_transformed():
    session = Session(
        Response({"data": [stat(10, 1, "20:30", 5, 1, 10), stat(20, 2, "30", 4, 2, -10)],
                  "meta": {"next_cursor": 99, "per_page": 100}}),
        Response({"data": [stat(11, 1, "19:30", 7, 3, 8), stat(21, 2, "10", 2, 1, -8)],
                  "meta": {"per_page": 100}}),
        Response({"data": TEAMS, "meta": {}})
    )
    source = BallDontLieSource(0, api_key="key", session=session)
    paced = []
    source._pace_request = lambda: paced.append(True)

    players = source.player_games(2024, SeasonType.REGULAR_SEASON)

    assert len(players) == 4
    assert players["SEASON_TYPE"].unique().tolist() == [GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON]]
    assert players.loc[players["PLAYER_ID"] == 10, "MATCHUP"].item() == "ATL vs. BOS"
    assert players.loc[players["PLAYER_ID"] == 20, "WL"].item() == "L"

    assert len(session.calls) == 3
    assert len(paced) == 3
    assert session.calls[0][1]["params"]["per_page"] == 100
    assert session.calls[1][1]["params"]["cursor"] == 99


def test_pagination_reports_its_start_and_each_twenty_fifth_page():
    pages = [Response({"data": [], "meta": {"next_cursor": page}}) for page in range(1, 25)]
    pages.append(Response({"data": [], "meta": {}}))
    source = BallDontLieSource(0, api_key="key", session=Session(*pages))
    reported = []
    source.set_progress_reporter(reported.append)

    source._pages("stats", description="1985 regular season player games")

    assert reported == [
        "1985 regular season player games: fetching raw API pages",
        "1985 regular season player games: fetched 0 raw API rows across 25 pages"
    ]


def test_player_game_batches_commit_one_game_group_before_the_next_group_fails():
    game_count = balldontlie_source.STAT_GAME_IDS_PER_REQUEST + 1
    game_ids = list(range(1, game_count + 1))
    first_group = []
    for game_id in game_ids[:-1]:
        home = stat(10, 1, "20", 5, 1, 4)
        visitor = stat(20, 2, "30", 4, 2, -4)
        for row in (home, visitor):
            row["game"].update({"id": game_id, "date": "2024-10-22"})
        first_group.extend((home, visitor))

    session = Session(
        Response({"data": [
            {"id": game_id, "date": "2024-10-22", "postseason": False}
            for game_id in game_ids
        ], "meta": {}}),
        Response({"data": first_group, "meta": {}}),
        Response({"data": TEAMS, "meta": {}})
    )
    source = BallDontLieSource(0, api_key="key", session=session)
    source.retries = 1
    source.retry_interval = 0

    batches = source.player_game_batches(2024, SeasonType.REGULAR_SEASON)
    first = next(batches)

    assert first["GAME_ID"].nunique() == balldontlie_source.STAT_GAME_IDS_PER_REQUEST
    assert len(first) <= balldontlie_source.PLAYER_GAME_BATCH_SIZE
    assert session.calls[1][1]["params"]["game_ids[]"] == game_ids[:-1]

    with pytest.raises(SourceDataError, match="could not be fetched"):
        next(batches)

    assert session.calls[-1][1]["params"]["game_ids[]"] == [game_ids[-1]]


def test_player_game_batches_skip_an_all_rejected_group_and_continue():
    game_count = balldontlie_source.STAT_GAME_IDS_PER_REQUEST + 1
    game_ids = list(range(1, game_count + 1))
    incomplete = stat(10, 1, "20", 5, 1, 4)
    incomplete["game"]["id"] = game_ids[0]
    valid = [stat(30, 1, "20", 5, 1, 4), stat(40, 2, "30", 4, 2, -4)]
    for row in valid:
        row["game"]["id"] = game_ids[-1]

    session = Session(
        Response({"data": [
            {"id": game_id, "date": "2024-10-22", "postseason": False}
            for game_id in game_ids
        ], "meta": {}}),
        Response({"data": [incomplete], "meta": {}}),
        Response({"data": valid, "meta": {}}),
        Response({"data": TEAMS, "meta": {}})
    )
    source = BallDontLieSource(0, api_key="key", session=session)

    batches = list(source.player_game_batches(2024, SeasonType.REGULAR_SEASON))

    assert [batch["GAME_ID"].unique().tolist() for batch in batches] == [[game_ids[-1]]]
    assert session.calls[1][1]["params"]["game_ids[]"] == game_ids[:-1]
    assert session.calls[2][1]["params"]["game_ids[]"] == [game_ids[-1]]


def test_nonfinal_rows_are_not_box_scores():
    live = stat(10, 1, "20", 5, 1, 4)
    live["game"]["status"] = "2nd Qtr"
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [live], "meta": {}}))
    )

    assert source.player_games(2024, SeasonType.REGULAR_SEASON).empty


def test_final_games_without_participants_are_skipped():
    did_not_play = stat(11, 1, None, 0, 0, 0)
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [did_not_play], "meta": {}}))
    )

    assert source.player_games(2024, SeasonType.REGULAR_SEASON).empty

def test_player_info_fetches_one_player_when_the_directory_is_not_loaded():
    session = Session(Response({"data": {
        "id": 10,
        "first_name": "Ada",
        "last_name": "Player",
        "height": "6-4",
        "weight": "190",
        "position": "G",
        "draft_number": 7
    }}))
    source = BallDontLieSource(0, api_key="key", session=session)

    player = source.player_info(10)

    assert player["PLAYER_NAME"].item() == "Ada Player"
    assert session.calls[0][0].endswith("/players/10")

def test_all_incomplete_final_games_are_skipped():
    incomplete = stat(10, 1, "20", 5, 1, 4)
    incomplete.pop("ast")
    teammate = stat(11, 1, "20", 5, 1, 4)
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [incomplete, teammate, stat(20, 2, "30", 4, 2, -4)], "meta": {}}))
    )

    assert source.player_games(2024, SeasonType.REGULAR_SEASON).empty

def test_a_final_game_with_only_one_team_is_skipped():
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [stat(10, 1, "20", 5, 1, 4)], "meta": {}}))
    )

    assert source.player_games(2024, SeasonType.REGULAR_SEASON).empty


def test_malformed_successful_page_is_a_fatal_source_error():
    source = BallDontLieSource(0, api_key="key", session=Session(Response({"data": {}})))

    with pytest.raises(SourceDataError, match="expected a data list"):
        source.player_games(2024, SeasonType.REGULAR_SEASON)


def test_malformed_player_stat_rows_are_reported_and_skipped():
    malformed = stat(10, 1, "20", 5, 1, 4)
    malformed.pop("game")
    valid = [stat(30, 1, "20", 5, 1, 4), stat(40, 2, "30", 4, 2, -4)]
    for row in valid:
        row["game"].update({"id": 18400002, "date": "2024-10-24"})
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(
            Response({"data": [None, malformed, *valid], "meta": {}}),
            Response({"data": TEAMS, "meta": {}})
        )
    )
    reported = []
    source.set_progress_reporter(reported.append)

    players = source.player_games(2024, SeasonType.REGULAR_SEASON)

    assert players["GAME_ID"].unique().tolist() == [18400002]
    assert [
        message for message in reported if "skipped malformed" in message
    ] == [
        "2024 regular season player games: skipped malformed player-stat row unknown on unknown: "
        "expected a player-stat object",
        "2024 regular season player games: skipped malformed player-stat row unknown on unknown: "
        "missing game metadata"
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    (("date", None), ("date", "20260101"), ("fgm", "not-a-number"), ("fgm", -1))
)
def test_invalid_final_game_values_are_skipped(field, value):
    first = stat(10, 1, "20", 5, 1, 4)
    second = stat(20, 2, "30", 4, 2, -4)
    target = first["game"] if field == "date" else first
    target[field] = value
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [first, second], "meta": {}}))
    )

    assert source.player_games(2024, SeasonType.REGULAR_SEASON).empty


def test_missing_page_metadata_is_a_fatal_source_error():
    source = BallDontLieSource(0, api_key="key", session=Session(Response({"data": []})))

    with pytest.raises(SourceDataError, match="expected metadata"):
        source._pages("stats")


def test_repeated_cursor_is_a_fatal_source_error():
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(
            Response({"data": [], "meta": {"next_cursor": 1}}),
            Response({"data": [], "meta": {"next_cursor": 1}})
        )
    )

    with pytest.raises(SourceDataError, match="repeated a cursor"):
        source.player_games(2024, SeasonType.REGULAR_SEASON)


def test_malformed_final_game_is_reported_without_discarding_valid_games():
    incomplete = stat(10, 1, "20:60", 5, 1, 4)
    valid = [stat(30, 1, "20", 5, 1, 4), stat(40, 2, "30", 4, 2, -4)]
    for row in valid:
        row["game"].update({"id": 18400002, "date": "2024-10-24"})
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(
            Response({"data": [incomplete, stat(20, 2, "30", 4, 2, -4), *valid], "meta": {}}),
            Response({"data": TEAMS, "meta": {}})
        )
    )
    reported = []
    source.set_progress_reporter(reported.append)

    players = source.player_games(2024, SeasonType.REGULAR_SEASON)

    assert players["GAME_ID"].unique().tolist() == [18400002]
    assert reported[-1] == (
        "2024 regular season player games: skipped malformed final game 18400001 on 2024-10-22: "
        "seconds must be from 0 through 59"
    )

def test_final_games_without_plus_minus_are_skipped():
    participants = [stat(10, 1, "30", 5, 1, None), stat(20, 2, "30", 4, 2, None)]
    did_not_play = stat(11, 1, "00", 0, 0, None)
    for field in (*balldontlie_source.STAT_COLUMNS, "plus_minus"):
        did_not_play.pop(field)
    for row in (*participants, did_not_play):
        row["game"].update({"id": 19500001, "date": "1995-11-03", "season": 1995})

    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(
            Response({"data": [*participants, did_not_play], "meta": {}}),
            Response({"data": TEAMS, "meta": {}})
        )
    )

    assert source.player_games(1995, SeasonType.REGULAR_SEASON).empty


def test_play_in_is_collected_with_regular_season_and_unsupported_phases_make_no_request():
    session = Session(Response({"data": [], "meta": {}}))
    source = BallDontLieSource(0, api_key="key", session=session)

    assert source.player_games(2024, SeasonType.PLAY_IN).empty
    assert source.player_games(2024, SeasonType.PRESEASON).empty
    source.player_games(2024, SeasonType.REGULAR_SEASON)

    assert len(session.calls) == 1
    assert session.calls[0][1]["params"]["postseason"] == "false"


def test_an_update_asks_the_service_for_its_date_range_rather_than_a_whole_season():
    """
    The hourly job wants one day. Filtering a whole season's game list here instead would be a
    dozen pages of it every hour, on a service paced at sixty requests a minute.
    """

    session = Session(
        Response({"data": [{"id": 7, "date": "2024-10-22", "postseason": False}], "meta": {}}),
        Response({"data": [stat(10, 1, "20", 5, 1, 4), stat(20, 2, "30", 4, 2, -4)], "meta": {}}),
        Response({"data": TEAMS, "meta": {}})
    )
    source = BallDontLieSource(0, api_key="key", session=session)

    list(source.player_game_batches(
        2024, SeasonType.REGULAR_SEASON, date(2024, 10, 21), date(2024, 10, 22)
    ))

    games = session.calls[0][1]["params"]
    assert (games["start_date"], games["end_date"]) == ("2024-10-21", "2024-10-22")


def test_the_two_phases_of_one_season_read_one_game_list():
    """Both ask the same question, and the answer is the most expensive page in a collection run."""

    session = Session(
        Response({"data": [{"id": 7, "date": "2024-10-22", "postseason": False}], "meta": {}}),
        Response({"data": [stat(10, 1, "20", 5, 1, 4), stat(20, 2, "30", 4, 2, -4)], "meta": {}}),
        Response({"data": TEAMS, "meta": {}})
    )
    source = BallDontLieSource(0, api_key="key", session=session)

    list(source.player_game_batches(2024, SeasonType.REGULAR_SEASON))
    list(source.player_game_batches(2024, SeasonType.PLAYOFFS))

    assert [url.rsplit("/", 1)[-1] for url, _ in session.calls] == ["games", "stats", "teams"]


def test_rate_limit_response_waits_for_retry_after(monkeypatch):
    waited = []
    monkeypatch.setattr(balldontlie_source.time, "sleep", waited.append)
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(
            Response({}, status=429, headers={"Retry-After": "7"}),
            Response({"data": TEAMS, "meta": {}})
        )
    )

    assert len(source.teams()) == 2
    assert 7 in waited


def test_rate_limit_reset_header_is_an_epoch_time(monkeypatch):
    monkeypatch.setattr(balldontlie_source.time, "time", lambda: 1000)
    source = BallDontLieSource(0, api_key="key", session=Session())

    wait = source._rate_limit_wait(Response({}, headers={"x-ratelimit-reset": "1012"}))

    assert wait == 12


def test_an_unreadable_rate_limit_header_falls_back_and_is_capped(monkeypatch):
    """Nothing watches an hourly job, so a header it cannot read must not park it for an afternoon."""

    monkeypatch.setattr(balldontlie_source.time, "time", lambda: 1000)
    source = BallDontLieSource(0, api_key="key", session=Session())

    assert source._rate_limit_wait(Response({}, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})) == (
        source.retry_interval
    )
    assert source._rate_limit_wait(Response({}, headers={"x-ratelimit-reset": "9999999"})) == (
        balldontlie_source.MAX_RATE_LIMIT_WAIT_SECONDS
    )


def test_a_listing_the_service_will_not_answer_for_is_not_held_as_an_empty_one(monkeypatch):
    """
    Both listings are held for the rest of the run, so a failed one has to stop it.

    Holding an empty team list would write every matchup that run collects with a number in place of
    the opponent's tricode, and the run would carry on as though nothing had happened.
    """

    monkeypatch.setattr(balldontlie_source.time, "sleep", lambda _: None)
    session = Session(*[Response({}, status=500) for _ in range(BallDontLieSource.retries)])
    source = BallDontLieSource(0, api_key="key", session=session)

    with pytest.raises(SourceDataError, match="would not answer for the teams list"):
        source.teams()

    assert len(session.calls) == BallDontLieSource.retries


def test_a_player_the_service_does_not_know_is_answered_rather_than_stopping_the_run():
    """
    A run sweeps every player who has a stored game, and an archive can hold one this service never
    issued an identifier for. That is an answer of nobody, not a reason to stop collecting.
    """

    session = Session(Response({}, status=404))
    source = BallDontLieSource(0, api_key="key", session=session)

    assert source.player_info(999_999) is None
    assert len(session.calls) == 1


def test_missing_key_is_reported_before_a_request(monkeypatch):
    monkeypatch.delenv("BALL_DONT_LIE_KEY", raising=False)
    monkeypatch.setattr(balldontlie_source, "load_dotenv", lambda *args, **kwargs: False)

    with pytest.raises(ValueError, match="BALL_DONT_LIE_KEY"):
        BallDontLieSource(session=Session())


def test_rejected_key_is_a_fatal_error():
    source = BallDontLieSource(
        0,
        api_key="bad-key",
        session=Session(Response({}, status=401))
    )

    with pytest.raises(SourceAuthenticationError, match="rejected"):
        source.teams()


def test_non_rate_limit_client_errors_are_fatal_without_retrying():
    session = Session(Response({}, status=403))
    source = BallDontLieSource(0, api_key="key", session=session)

    with pytest.raises(SourceDataError, match="HTTP 403"):
        source.teams()

    assert len(session.calls) == 1


def test_rosters_read_the_active_list_and_lay_the_injury_report_over_it():
    """
    Neither fetch is enough alone: the active list says who is rostered and nothing about fitness,
    and the report says who is hurt without naming everybody who is not.
    """

    active = [
        {"id": 10, "team": {"id": 1}},
        {"id": 11, "team": {"id": 2}}
    ]
    injuries = [
        {"player": {"id": 11, "team_id": 2}, "status": "Out"},
        {"player": {"id": 12, "team_id": 1}, "status": "Doubtful"}
    ]
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(
            Response({"data": active, "meta": {}}),
            Response({"data": injuries, "meta": {}})
        )
    )

    held = {entry.player_id: entry for entry in source.rosters()}

    assert held[10].team_id == 1 and held[10].playing
    assert held[11].team_id == 2 and not held[11].playing
    # Named only by the report, and placed by the team the report itself gives them.
    assert held[12].team_id == 1 and not held[12].playing


def test_an_injured_player_on_no_roster_and_no_team_is_dropped():
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(
            Response({"data": [{"id": 10, "team": {"id": 1}}], "meta": {}}),
            Response({"data": [{"player": {"id": 12}, "status": "Out"}], "meta": {}})
        )
    )

    assert {entry.player_id for entry in source.rosters()} == {10}


def test_a_roster_listing_the_service_will_not_answer_for_stops_the_run():
    """An empty roster table would read as a league with nobody on it, so nothing is written."""

    source = BallDontLieSource(0, api_key="key", session=Session(Response({}, status=500)))
    source.retries = 1

    with pytest.raises(SourceDataError):
        source.rosters()


def test_nba_api_publishes_no_roster_feed():
    """nba.com carries none, so an archive collected through it predicts as it always did."""

    assert NBAApiSource().rosters() is None


def test_schedule_maps_status_tipoff_and_playoff_phase():
    scheduled = {
        "id": 7,
        "date": "2025-04-20",
        "datetime": "2025-04-20T19:00:00.000Z",
        "status": "7:00 pm ET",
        "period": 0,
        "postseason": True,
        "postponed": False,
        "home_team": {"id": 1},
        "visitor_team": {"id": 2}
    }
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [scheduled], "meta": {}}))
    )

    game = source.schedule(2024)[0]

    assert game.status is GameStatus.SCHEDULED
    assert game.game.season_type is SeasonType.PLAYOFFS
    assert game.tipoff.utcoffset().total_seconds() == 0


def test_explicit_phase_is_used_when_a_provider_game_id_has_no_phase_prefix():
    rows = pd.DataFrame({"GAME_ID": [18400001], "SEASON_TYPE": ["2"]})

    built = season_columns.add_encoded_season_type_columns(rows, "GAME_ID", "SEASON_TYPE")

    assert built[SeasonType.REGULAR_SEASON.value].item() == 1
    assert built[SeasonType.PRESEASON.value].item() == 0


def test_source_registry_keeps_nba_api_and_defaults_to_balldontlie():
    assert sources.DEFAULT_SOURCE == "balldontlie"
    assert set(sources.ALL_SOURCES) >= {"balldontlie", "nba_api"}


def test_nba_api_game_collection_still_supplies_an_explicit_phase(monkeypatch):
    class GameLog:
        def __init__(self, **kwargs):
            pass

        def get_data_frames(self):
            return [pd.DataFrame([{"GAME_ID": 22400001}])]

    monkeypatch.setattr(nba_api_source, "LeagueGameLog", GameLog)

    rows = NBAApiSource(0).player_games(2024, SeasonType.REGULAR_SEASON)

    assert rows["SEASON_TYPE"].item() == GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON]


def test_deployment_passes_the_key_only_to_the_balldontlie_job():
    deployment = Path(__file__).resolve().parents[2] / "deploy"
    compose = (deployment / "docker-compose.yml").read_text(encoding="utf-8")
    jobs = compose[compose.index("  jobs:"):]

    key_lines = [line for line in compose.splitlines() if line.lstrip().startswith("BALL_DONT_LIE_KEY:")]
    assert len(key_lines) == 1
    assert "BALL_DONT_LIE_KEY:" in jobs
    assert 'command: ["nba-update-serving"]' in jobs
    assert "nba-collect --source balldontlie all" not in jobs
    assert "BALL_DONT_LIE_KEY=" in (deployment / ".env.example").read_text(encoding="utf-8")


def test_scheduled_jobs_are_locked_and_skip_non_game_days():
    crontab = (Path(__file__).resolve().parents[2] / "deploy" / "crontab").read_text(encoding="utf-8")

    assert "nba-collect --source balldontlie schedule" in crontab
    assert "nba-update-serving" not in crontab
    assert crontab.count("flock") == 4
    assert "/var/lock" not in crontab
    assert "/var/log" not in crontab


def test_data_directory_cannot_mix_provider_identifiers():
    source_identity.claim("balldontlie")

    with pytest.raises(RuntimeError, match="belongs to balldontlie"):
        source_identity.claim("nba_api")


def test_unmarked_legacy_databases_can_only_be_claimed_by_nba_api():
    paths.DATABASE_DIRECTORY.mkdir(parents=True)
    (paths.DATABASE_DIRECTORY / "legacy.db").write_bytes(b"sqlite")

    with pytest.raises(RuntimeError, match="legacy nba_api"):
        source_identity.claim("balldontlie")

    source_identity.claim("nba_api")
    assert source_identity.MARKER.read_text(encoding="utf-8").strip() == "nba_api"
