"""BALLDONTLIE's NBA service, using only endpoints available on ALL-STAR."""

import os
import time
from math import isfinite
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import requests
from dotenv import load_dotenv

from nba_ml import season
from nba_ml.entities import Game, GameStatus, Player, ScheduledGame, Team
from nba_ml.season import SeasonType
from nba_ml.sources.base import (
    DataSource,
    PLAYER_GAME_BATCH_SIZE,
    SourceAuthenticationError,
    SourceDataError
)

BASE_URL = "https://api.balldontlie.io/v1"
PER_PAGE = 100
STAT_GAME_IDS_PER_REQUEST = 100
REQUEST_TIMEOUT = (10, 30)
MAX_RATE_LIMIT_WAIT_SECONDS = 120

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
            seconds = int(seconds)
            if not 0 <= seconds < 60:
                raise ValueError("seconds must be from 0 through 59")
            minutes = int(whole_minutes) + seconds / 60

    if not isfinite(minutes) or minutes < 0:
        raise ValueError("minutes must be a finite nonnegative value")

    return minutes or None


def _whole_number(value: Any, minimum: int | None = None) -> int:
    """A box-score count, which cannot be a boolean, fraction or non-finite number."""

    if isinstance(value, bool):
        raise ValueError("a boolean is not a box-score count")
    number = float(value)
    if not isfinite(number) or not number.is_integer():
        raise ValueError("a box-score count must be finite and whole")
    if minimum is not None and number < minimum:
        raise ValueError(f"a box-score count cannot be below {minimum}")
    return int(number)


def _number(value: str | None) -> float | None:
    """A response header read as a number, or None where it is absent or is not one."""

    try:
        return None if value is None else float(value)
    except ValueError:
        return None


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
        self._games: tuple[tuple, list[Any]] | None = None

    def _rate_limit_wait(self, response: requests.Response) -> float:
        """
        How long to wait out a rate limit, read off whichever header the service sent.

        A header that is not a number, or one naming a time far away, is capped rather than
        believed. Nothing watches an hourly job, so a bad header must not park it for an afternoon.
        """

        seconds = _number(response.headers.get("Retry-After"))
        if seconds is None:
            reset = _number(response.headers.get("x-ratelimit-reset"))
            seconds = self.retry_interval if reset is None else reset - time.time()

        return min(max(seconds, 0.0), MAX_RATE_LIMIT_WAIT_SECONDS)

    def _page(
        self,
        endpoint: str,
        params: dict[str, Any],
        allow_missing: bool = False
        ) -> dict[str, Any] | None:
        """
        Args:
            allow_missing answers None where the service holds nothing under this address, rather
            than stopping the run. Only an address naming one record can be missing.
        """

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
            if response.status_code == 404 and allow_missing:
                return None
            if response.status_code != 429 and 400 <= response.status_code < 500:
                raise SourceDataError(f"BALLDONTLIE request for {endpoint} failed with HTTP {response.status_code}.")
            if response.status_code != 429:
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError as error:
                    raise SourceDataError(f"BALLDONTLIE returned invalid JSON for {endpoint}.") from error

            if attempt + 1 < self.retries:
                time.sleep(self._rate_limit_wait(response))

        response.raise_for_status()
        raise AssertionError("unreachable")

    def _pages(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        description: str | None = None
        ) -> list[Any]:
        params = dict(params or {})
        params["per_page"] = PER_PAGE
        rows: list[Any] = []
        page_number = 0
        seen_cursors: set[int | str] = set()

        if description is not None:
            self._report_progress(f"{description}: fetching raw API pages")

        while True:
            page = self._page(endpoint, params)
            if not isinstance(page, dict) or not isinstance(page.get("data"), list):
                raise SourceDataError(f"BALLDONTLIE returned a malformed page for {endpoint}: expected a data list.")
            if endpoint != "stats" and any(not isinstance(row, dict) for row in page["data"]):
                raise SourceDataError(f"BALLDONTLIE returned malformed rows for {endpoint}: expected objects.")
            metadata = page.get("meta")
            if endpoint == "stats" and not isinstance(metadata, dict):
                raise SourceDataError(f"BALLDONTLIE returned a malformed page for {endpoint}: expected metadata.")
            if metadata is None:
                return [*rows, *page["data"]]
            if not isinstance(metadata, dict):
                raise SourceDataError(f"BALLDONTLIE returned a malformed page for {endpoint}: expected metadata.")
            rows.extend(page["data"])
            page_number += 1
            if description is not None and page_number % 25 == 0:
                self._report_progress(
                    f"{description}: fetched {len(rows)} raw API rows across {page_number} pages"
                )
            cursor = metadata.get("next_cursor")
            if cursor is None:
                return rows
            if isinstance(cursor, bool) or not isinstance(cursor, (int, str)):
                raise SourceDataError(f"BALLDONTLIE returned an invalid cursor for {endpoint}.")
            if cursor in seen_cursors:
                raise SourceDataError(f"BALLDONTLIE repeated a cursor for {endpoint}.")
            seen_cursors.add(cursor)
            params["cursor"] = cursor

    @staticmethod
    def _by_id(endpoint: str, rows: list[Any] | None) -> dict[int, dict[str, Any]]:
        """
        A whole listing keyed by its own identifiers.

        A listing the service would not answer for stops the run rather than being held as an empty
        one. Both listings are kept for the rest of the run, so an empty one would read as a service
        that has no teams or no players and quietly change everything written afterwards.
        """

        if rows is None:
            raise SourceDataError(f"BALLDONTLIE would not answer for the {endpoint} list.")

        try:
            return {int(row["id"]): row for row in rows}
        except (KeyError, TypeError, ValueError) as error:
            raise SourceDataError(f"BALLDONTLIE returned malformed {endpoint} rows.") from error

    def _team_rows(self) -> dict[int, dict[str, Any]]:
        if self._teams is None:
            self._teams = self._by_id("teams", self._fetch(
                lambda: self._pages("teams", description="teams"),
                "teams",
                pace=False
            ))
        return self._teams

    def teams(self) -> list[Team]:
        try:
            return [
                Team(team_id, row["full_name"], row["abbreviation"])
                for team_id, row in self._team_rows().items()
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise SourceDataError("BALLDONTLIE returned malformed team rows.") from error

    def _player_rows(self) -> dict[int, dict[str, Any]]:
        if self._players is None:
            self._players = self._by_id("players", self._fetch(
                lambda: self._pages("players", description="players"),
                "players",
                pace=False
            ))
        return self._players

    def players(self) -> list[Player]:
        return [Player(player_id, _name(row)) for player_id, row in self._player_rows().items()]

    def player_info(self, player_id: int) -> pd.DataFrame | None:
        if self._players is None:
            response = self._fetch(
                lambda: self._page(f"players/{player_id}", {}, allow_missing=True),
                f"player {player_id}"
            )
            player = None if response is None else response.get("data")
        else:
            player = self._players.get(player_id)

        if player is None:
            return None
        if not isinstance(player, dict):
            raise SourceDataError(f"BALLDONTLIE returned a malformed player row for {player_id}.")

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
        ) -> list[Any] | None:
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

    def _season_games(
        self,
        season_year: int,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> list[Any] | None:
        """
        The games of one season the service lists, played or not, narrowed to the dates asked for.

        The dates go to the service rather than being filtered here, so an hourly update reads one
        page instead of a whole season of them. The last answer is held, because the two phases of a
        season ask the same question and one full-season list is a few hundred kilobytes.
        """

        key = (season_year, date_from, date_to)
        if self._games is not None and self._games[0] == key:
            return self._games[1]

        params: dict[str, Any] = {"seasons[]": season_year}
        if date_from is not None:
            params["start_date"] = date_from.isoformat()
        if date_to is not None:
            params["end_date"] = date_to.isoformat()

        rows = self._fetch(
            lambda: self._pages("games", params, f"{season_year} games"),
            f"the {season_year} game list",
            pace=False
        )
        if rows is not None:
            self._games = (key, rows)

        return rows

    def _player_game_ids(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None,
        date_to: date | None
        ) -> list[int] | None:
        postseason = self._postseason(season_type)
        if postseason is None:
            return []

        rows = self._season_games(season_year, date_from, date_to)
        if rows is None:
            return None

        try:
            game_ids = []
            for row in rows:
                game_date = date.fromisoformat(row["date"])
                if (
                    row.get("postseason") == postseason
                    and (date_from is None or game_date >= date_from)
                    and (date_to is None or game_date <= date_to)
                ):
                    game_ids.append(_whole_number(row["id"], 1))
        except (KeyError, TypeError, ValueError) as error:
            raise SourceDataError(
                f"BALLDONTLIE returned a malformed game list for {season_year} {season_type.value.lower()}."
            ) from error

        return game_ids

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

    def _player_game_rows(
        self,
        rows: list[Any],
        season_type: SeasonType
        ) -> tuple[pd.DataFrame, int]:
        rows, rejected_games = self._complete_game_rows(rows)
        games = []
        for row in rows:
            minutes = _minutes(row.get("min"))
            game = row["game"]
            if minutes is None or game.get("status") != "Final":
                continue

            matchup, result = self._matchup(row)
            games.append({
                "PLAYER_ID": _whole_number(row["player"]["id"], 1),
                "GAME_ID": _whole_number(game["id"], 1),
                "TEAM_ID": _whole_number(row["team"]["id"], 1),
                "GAME_DATE": game["date"],
                "SEASON_TYPE": season.GAME_ID_PREFIXES[season_type],
                "MATCHUP": matchup,
                "WL": result,
                "MIN": minutes,
                **{stored: _whole_number(row.get(source) or 0, 0) for source, stored in STAT_COLUMNS.items()},
                "PLUS_MINUS": _whole_number(row["plus_minus"])
            })
        return pd.DataFrame(games), rejected_games

    @staticmethod
    def _complete_game_rows(
        rows: list[Any]
        ) -> tuple[list[dict[str, Any]], list[tuple[Any, Any, str]]]:
        """Keep final games only when both sides have every model input."""

        games: dict[int, list[dict[str, Any]]] = {}
        rejected_games: list[tuple[Any, Any, str]] = []
        for row in rows:
            if not isinstance(row, dict):
                rejected_games.append((None, None, "expected a player-stat object"))
                continue
            game = row.get("game")
            if not isinstance(game, dict):
                rejected_games.append((None, None, "missing game metadata"))
                continue
            missing = [
                field
                for field in (
                    "id", "status", "date", "home_team_id", "visitor_team_id",
                    "home_team_score", "visitor_team_score"
                )
                if field not in game
            ]
            if missing:
                rejected_games.append((game.get("id"), game.get("date"), f"missing game metadata: {missing[0]}"))
                continue
            if game["status"] != "Final":
                continue

            try:
                games.setdefault(_whole_number(game["id"], 1), []).append(row)
            except (TypeError, ValueError) as error:
                rejected_games.append((game.get("id"), game.get("date"), str(error)))

        completed = []
        for game_rows in games.values():
            game = game_rows[0]["game"]
            try:
                season.from_date_string(game["date"])
                _whole_number(game["home_team_id"], 1)
                _whole_number(game["visitor_team_id"], 1)
                _whole_number(game["home_team_score"], 0)
                _whole_number(game["visitor_team_score"], 0)
                players = [row for row in game_rows if _minutes(row.get("min")) is not None]
            except (TypeError, ValueError) as error:
                rejected_games.append((game["id"], game.get("date"), str(error)))
                continue
            try:
                for row in players:
                    player = row.get("player")
                    team = row.get("team")
                    if isinstance(player, dict) and "id" in player:
                        _whole_number(player["id"], 1)
                    if isinstance(team, dict) and "id" in team:
                        _whole_number(team["id"], 1)
                    for field in REQUIRED_PLAYER_STAT_FIELDS:
                        if row.get(field) is not None:
                            _minutes(row[field]) if field == "min" else _whole_number(
                                row[field], None if field == "plus_minus" else 0
                            )
                incomplete = (
                    not players
                    or any(
                        not isinstance(row.get("player"), dict) or "id" not in row["player"]
                        for row in players
                    )
                    or any(
                        not isinstance(row.get("team"), dict)
                        or "id" not in row["team"]
                        or "abbreviation" not in row["team"]
                        for row in players
                    )
                    or any(
                        row.get(field) is None
                        for row in players
                        for field in REQUIRED_PLAYER_STAT_FIELDS
                    )
                    or {
                        _whole_number(row["team"]["id"], 1)
                        for row in players
                    } != {
                        _whole_number(game["home_team_id"], 1),
                        _whole_number(game["visitor_team_id"], 1)
                    }
                )
            except (TypeError, ValueError) as error:
                rejected_games.append((game["id"], game.get("date"), str(error)))
                continue

            if incomplete:
                rejected_games.append((game["id"], game.get("date"), "incomplete player statistics"))
                continue

            completed.extend(players)

        return completed, rejected_games

    def _report_rejected_player_games(
        self,
        season_year: int,
        season_type: SeasonType,
        rejected_games: list[tuple[Any, Any, str]]
        ):
        description = f"{season_year} {season_type.value.lower().replace('_', ' ')} player games"
        for game_id, game_date, reason in rejected_games:
            target = "player-stat row" if game_id is None else "final game"
            identifier = "unknown" if game_id is None else game_id
            game_day = "unknown" if game_date is None else game_date
            self._report_progress(
                f"{description}: skipped malformed {target} {identifier} on {game_day}: {reason}"
            )

    def player_game_batches(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> Iterator[pd.DataFrame]:
        """Yield complete player games in database-sized batches."""

        game_ids = self._player_game_ids(season_year, season_type, date_from, date_to)
        if game_ids is None:
            phase = season_type.value.lower().replace("_", " ")
            raise SourceDataError(f"{season_year} {phase} player games could not be fetched.")

        description = f"{season_year} {season_type.value.lower().replace('_', ' ')} player games"
        for start in range(0, len(game_ids), STAT_GAME_IDS_PER_REQUEST):
            group_ids = game_ids[start:start + STAT_GAME_IDS_PER_REQUEST]
            group_description = f"{description}: fetching game group {start // STAT_GAME_IDS_PER_REQUEST + 1}"
            rows = self._fetch(
                lambda: self._pages("stats", {"game_ids[]": group_ids}, group_description),
                group_description,
                pace=False
            )
            if rows is None:
                raise SourceDataError(f"{description} could not be fetched.")

            games, rejected_games = self._player_game_rows(rows, season_type)
            self._report_rejected_player_games(season_year, season_type, rejected_games)
            if games.empty:
                continue

            batch_parts: list[pd.DataFrame] = []
            batch_size = 0
            for _, game_rows in games.groupby("GAME_ID", sort=False):
                if len(game_rows) > PLAYER_GAME_BATCH_SIZE:
                    raise SourceDataError(
                        f"{description} game {game_rows['GAME_ID'].iloc[0]} has too many player rows for one batch."
                    )
                if batch_size and batch_size + len(game_rows) > PLAYER_GAME_BATCH_SIZE:
                    yield pd.concat(batch_parts, ignore_index=True)
                    batch_parts = []
                    batch_size = 0
                batch_parts.append(game_rows)
                batch_size += len(game_rows)
                if batch_size == PLAYER_GAME_BATCH_SIZE:
                    yield pd.concat(batch_parts, ignore_index=True)
                    batch_parts = []
                    batch_size = 0

            if batch_parts:
                yield pd.concat(batch_parts, ignore_index=True)

    def player_games(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> pd.DataFrame | None:
        rows = self._stats(season_year, season_type, date_from, date_to)
        if rows is None:
            return None

        games, rejected_games = self._player_game_rows(rows, season_type)
        self._report_rejected_player_games(season_year, season_type, rejected_games)

        return games

    def schedule(self, season_year: int) -> list[ScheduledGame] | None:
        rows = self._season_games(season_year)
        if rows is None:
            return None

        try:
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
        except (KeyError, TypeError, ValueError) as error:
            raise SourceDataError(f"BALLDONTLIE returned malformed schedule rows for {season_year}.") from error

        return games
