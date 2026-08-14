"""BALLDONTLIE's NBA service, using only endpoints available on ALL-STAR."""

import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

from nba_ml import season
from nba_ml.entities import Game, GameStatus, Player, ScheduledGame, Team
from nba_ml.season import SeasonType
from nba_ml.sources.base import DataSource, SourceAuthenticationError

BASE_URL = "https://api.balldontlie.io/v1"
PER_PAGE = 100
REQUEST_TIMEOUT = (10, 30)

STAT_COLUMNS = {
    "fgm": "FGM",
    "fga": "FGA",
    "fg3m": "FG3M",
    "fg3a": "FG3A",
    "ftm": "FTM",
    "fta": "FTA",
    "oreb": "OREB",
    "dreb": "DREB",
    "ast": "AST",
    "stl": "STL",
    "blk": "BLK",
    "turnover": "TOV",
    "pf": "PF"
}

REQUIRED_PLAYER_STAT_FIELDS = ("min", *STAT_COLUMNS, "plus_minus")
"""Fields every player row needs before a game can enter a model's archive."""


def _minutes(value: Any) -> float | None:
    """Minutes as a number. An empty or zero value means the player did not appear."""

    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        minutes = float(value)
    else:
        text = str(value)
        if ":" not in text:
            minutes = float(text)
        else:
            whole_minutes, seconds = text.split(":", 1)
            minutes = int(whole_minutes) + int(seconds) / 60

    return minutes or None


def _name(player: dict[str, Any]) -> str:
    return " ".join(part for part in (player.get("first_name"), player.get("last_name")) if part)


class BallDontLieSource(DataSource):
    name = "balldontlie"
    oldest_season = 1946
    request_interval = 1.05

    def __init__(
        self,
        request_interval: float | None = None,
        api_key: str | None = None,
        session: requests.Session | None = None
        ):
        super().__init__(request_interval)

        load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=False)
        self.api_key = api_key or os.environ.get("BALL_DONT_LIE_KEY")
        if not self.api_key:
            raise ValueError("BALL_DONT_LIE_KEY is required for the balldontlie data source.")

        self.session = session or requests.Session()
        self._players: dict[int, dict[str, Any]] | None = None
        self._teams: dict[int, dict[str, Any]] | None = None

    def _rate_limit_wait(self, response: requests.Response) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            return max(float(retry_after), 0.0)

        reset = response.headers.get("x-ratelimit-reset")
        return max(float(reset) - time.time(), 0.0) if reset is not None else self.retry_interval

    def _page(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self.retries):
            self._pace_request()
            response = self.session.get(
                f"{BASE_URL}/{endpoint}",
                headers={"Authorization": self.api_key},
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 401:
                raise SourceAuthenticationError(
                    "BALLDONTLIE rejected the API key or this endpoint is unavailable on the account tier."
                )
            if response.status_code != 429:
                response.raise_for_status()
                return response.json()

            if attempt + 1 < self.retries:
                time.sleep(self._rate_limit_wait(response))

        response.raise_for_status()
        raise AssertionError("unreachable")

    def _pages(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        description: str | None = None
        ) -> list[dict[str, Any]]:
        params = dict(params or {})
        params["per_page"] = PER_PAGE
        rows: list[dict[str, Any]] = []
        page_number = 0

        if description is not None:
            self._report_progress(f"{description}: fetching pages")

        while True:
            page = self._page(endpoint, params)
            rows.extend(page.get("data", []))
            page_number += 1
            if description is not None and page_number % 25 == 0:
                self._report_progress(f"{description}: fetched {len(rows)} rows across {page_number} pages")
            cursor = page.get("meta", {}).get("next_cursor")
            if cursor is None:
                return rows
            params["cursor"] = cursor

    def _team_rows(self) -> dict[int, dict[str, Any]]:
        if self._teams is None:
            rows = self._fetch(
                lambda: self._pages("teams", description="teams"),
                "teams",
                pace=False
            )
            self._teams = {} if rows is None else {int(row["id"]): row for row in rows}
        return self._teams

    def teams(self) -> list[Team]:
        return [
            Team(team_id, row["full_name"], row["abbreviation"])
            for team_id, row in self._team_rows().items()
        ]

    def _player_rows(self) -> dict[int, dict[str, Any]]:
        if self._players is None:
            rows = self._fetch(
                lambda: self._pages("players", description="players"),
                "players",
                pace=False
            )
            self._players = {} if rows is None else {int(row["id"]): row for row in rows}
        return self._players

    def players(self) -> list[Player]:
        return [Player(player_id, _name(row)) for player_id, row in self._player_rows().items()]

    def player_info(self, player_id: int) -> pd.DataFrame | None:
        if self._players is None:
            response = self._fetch(
                lambda: self._page(f"players/{player_id}", {}),
                f"player {player_id}"
            )
            player = None if response is None else response.get("data")
        else:
            player = self._players.get(player_id)

        if player is None:
            return None

        return pd.DataFrame([{
            "PERSON_ID": player_id,
            "PLAYER_NAME": _name(player),
            "HEIGHT": player.get("height"),
            "WEIGHT": player.get("weight"),
            "POSITION": player.get("position"),
            "FROM_YEAR": None,
            "TO_YEAR": None,
            "BIRTHDATE": None,
            "DRAFT_NUMBER": player.get("draft_number") or "Undrafted"
        }])

    @staticmethod
    def _postseason(season_type: SeasonType) -> bool | None:
        if season_type is SeasonType.REGULAR_SEASON:
            return False
        if season_type is SeasonType.PLAYOFFS:
            return True
        return None

    def _stats(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None,
        date_to: date | None
        ) -> list[dict[str, Any]] | None:
        postseason = self._postseason(season_type)
        if postseason is None:
            return []

        params: dict[str, Any] = {
            "seasons[]": season_year,
            "postseason": str(postseason).lower()
        }
        if date_from is not None:
            params["start_date"] = date_from.isoformat()
        if date_to is not None:
            params["end_date"] = date_to.isoformat()

        return self._fetch(
            lambda: self._pages("stats", params, f"{season_year} {season_type.value.lower()} player games"),
            f"the {season_year} {season_type.value.lower()}",
            pace=False
        )

    def _matchup(self, row: dict[str, Any]) -> tuple[str, str]:
        game = row["game"]
        team = row["team"]
        team_id = int(team["id"])
        home = team_id == int(game["home_team_id"])
        opponent_id = int(game["visitor_team_id"] if home else game["home_team_id"])
        opponent = self._team_rows().get(opponent_id, {})
        separator = "vs." if home else "@"
        return f"{team['abbreviation']} {separator} {opponent.get('abbreviation', opponent_id)}", (
            "W" if (
                int(game["home_team_score"]) > int(game["visitor_team_score"])
            ) == home else "L"
        )

    def _player_game_rows(self, rows: list[dict[str, Any]], season_type: SeasonType) -> pd.DataFrame:
        rows = self._complete_game_rows(rows)
        games = []
        for row in rows:
            minutes = _minutes(row.get("min"))
            game = row["game"]
            if minutes is None or game.get("status") != "Final":
                continue

            matchup, result = self._matchup(row)
            games.append({
                "PLAYER_ID": int(row["player"]["id"]),
                "GAME_ID": int(game["id"]),
                "TEAM_ID": int(row["team"]["id"]),
                "GAME_DATE": game["date"],
                "SEASON_TYPE": season.GAME_ID_PREFIXES[season_type],
                "MATCHUP": matchup,
                "WL": result,
                "MIN": minutes,
                **{stored: row.get(source) or 0 for source, stored in STAT_COLUMNS.items()},
                "PLUS_MINUS": row.get("plus_minus")
            })
        return pd.DataFrame(games)

    @staticmethod
    def _complete_game_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep final games only when both sides have every model input."""

        games: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            game = row.get("game")
            if game is None or game.get("status") != "Final":
                continue

            games.setdefault(int(game["id"]), []).append(row)

        completed = []
        for game_rows in games.values():
            players = [row for row in game_rows if _minutes(row.get("min")) is not None]
            if (
                any(row.get("team") is None for row in players)
                or any(
                    row.get(field) is None
                    for row in players
                    for field in REQUIRED_PLAYER_STAT_FIELDS
                )
                or {
                    int(row["team"]["id"])
                    for row in players
                } != {
                    int(game_rows[0]["game"]["home_team_id"]),
                    int(game_rows[0]["game"]["visitor_team_id"])
                }
            ):
                continue

            completed.extend(players)

        return completed

    def player_games(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> pd.DataFrame | None:
        rows = self._stats(season_year, season_type, date_from, date_to)
        return None if rows is None else self._player_game_rows(rows, season_type)

    def schedule(self, season_year: int) -> list[ScheduledGame] | None:
        rows = self._fetch(
            lambda: self._pages("games", {"seasons[]": season_year}, f"{season_year} schedule"),
            f"the {season_year} schedule",
            pace=False
        )
        if rows is None:
            return None

        games = []
        for row in rows:
            if row.get("postponed"):
                status = GameStatus.SCHEDULED
            elif row.get("status") == "Final":
                status = GameStatus.FINAL
            elif int(row.get("period") or 0) > 0:
                status = GameStatus.LIVE
            else:
                status = GameStatus.SCHEDULED

            tipoff = row.get("datetime")
            games.append(ScheduledGame(
                id=int(row["id"]),
                game=Game(
                    date.fromisoformat(row["date"]),
                    int(row["home_team"]["id"]),
                    int(row["visitor_team"]["id"]),
                    SeasonType.PLAYOFFS if row.get("postseason") else SeasonType.REGULAR_SEASON
                ),
                status=status,
                tipoff=None if not tipoff else datetime.fromisoformat(tipoff.replace("Z", "+00:00"))
            ))
        return games
