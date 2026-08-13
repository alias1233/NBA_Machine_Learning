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
from nba_ml.sources.base import SourceAuthenticationError
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


def test_stats_are_paginated_transformed_once_and_summed_for_teams():
    session = Session(
        Response({"data": [stat(10, 1, "20:30", 5, 1, 10), stat(20, 2, "30", 4, 2, -10)],
                  "meta": {"next_cursor": 99, "per_page": 100}}),
        Response({"data": [stat(11, 1, "19:30", 7, 3, 8), stat(21, 2, "10", 2, 1, -8)],
                  "meta": {"per_page": 100}}),
        Response({"data": TEAMS})
    )
    source = BallDontLieSource(0, api_key="key", session=session)
    paced = []
    source._pace_request = lambda: paced.append(True)

    players, teams = source.game_rows(2024, SeasonType.REGULAR_SEASON)

    assert len(players) == 4
    assert players["SEASON_TYPE"].unique().tolist() == [GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON]]
    assert players.loc[players["PLAYER_ID"] == 10, "MATCHUP"].item() == "ATL vs. BOS"
    assert players.loc[players["PLAYER_ID"] == 20, "WL"].item() == "L"

    atl = teams.loc[teams["TEAM_ID"] == 1].iloc[0]
    assert atl["MIN"] == 40
    assert atl["FGM"] == 12
    assert atl["TOV"] == 4
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
        "1985 regular season player games: fetching pages",
        "1985 regular season player games: fetched 0 rows across 25 pages"
    ]


def test_nonfinal_and_did_not_play_rows_are_not_box_scores():
    live = stat(10, 1, "20", 5, 1, 4)
    live["game"]["status"] = "2nd Qtr"
    did_not_play = stat(11, 1, None, 0, 0, 0)
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [live, did_not_play], "meta": {}}))
    )

    assert source.player_games(2024, SeasonType.REGULAR_SEASON).empty

def test_a_game_with_a_missing_stat_is_excluded_from_both_stores():
    incomplete = stat(10, 1, "20", 5, 1, 4)
    incomplete.pop("ast")
    teammate = stat(11, 1, "20", 5, 1, 4)
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [incomplete, teammate, stat(20, 2, "30", 4, 2, -4)], "meta": {}}))
    )

    players, teams = source.game_rows(2024, SeasonType.REGULAR_SEASON)

    assert players.empty
    assert teams.empty

def test_a_game_with_only_one_team_is_excluded():
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(Response({"data": [stat(10, 1, "20", 5, 1, 4)], "meta": {}}))
    )

    assert source.player_games(2024, SeasonType.REGULAR_SEASON).empty


def test_play_in_is_collected_with_regular_season_and_unsupported_phases_make_no_request():
    session = Session(Response({"data": [], "meta": {}}))
    source = BallDontLieSource(0, api_key="key", session=session)

    assert source.player_games(2024, SeasonType.PLAY_IN).empty
    assert source.player_games(2024, SeasonType.PRESEASON).empty
    source.player_games(2024, SeasonType.REGULAR_SEASON)

    assert len(session.calls) == 1
    assert session.calls[0][1]["params"]["postseason"] == "false"


def test_rate_limit_response_waits_for_retry_after(monkeypatch):
    waited = []
    monkeypatch.setattr(balldontlie_source.time, "sleep", waited.append)
    source = BallDontLieSource(
        0,
        api_key="key",
        session=Session(
            Response({}, status=429, headers={"Retry-After": "7"}),
            Response({"data": TEAMS})
        )
    )

    assert len(source.teams()) == 2
    assert 7 in waited


def test_rate_limit_reset_header_is_an_epoch_time(monkeypatch):
    monkeypatch.setattr(balldontlie_source.time, "time", lambda: 1000)
    source = BallDontLieSource(0, api_key="key", session=Session())

    wait = source._rate_limit_wait(Response({}, headers={"x-ratelimit-reset": "1012"}))

    assert wait == 12


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
    assert "nba-collect --source balldontlie all" in jobs
    assert "BALL_DONT_LIE_KEY=" in (deployment / ".env.example").read_text(encoding="utf-8")


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
