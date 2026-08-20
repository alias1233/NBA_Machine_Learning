"""
What every NBA data source has to provide.

A source is the only part of the pipeline that talks to an outside service. It hands back rows named
the way the stores hold them, so swapping one source for another changes nothing downstream. Rate
limiting and retrying live here, because they are properties of the service being asked.

A source only fetches. Finding a player or a team by name is a question about what is already
stored, so it lives in the stores and needs no service at all.
"""

import time
from abc import ABC, abstractmethod
from datetime import date
from typing import Callable, Iterable, TypeVar

import pandas as pd

from nba_ml import season
from nba_ml.entities import Player, RosterEntry, ScheduledGame, Team
from nba_ml.season import SeasonType

Fetched = TypeVar("Fetched")

PLAYER_GAME_BATCH_SIZE = 2_500
"""Maximum player-game rows stored in one transaction."""

class SourceAuthenticationError(RuntimeError):
    """The source rejected its API key or the account tier cannot use the endpoint."""

class SourceDataError(RuntimeError):
    """The source returned data that cannot safely enter the archive."""

class DataSource(ABC):
    """
    One provider of NBA data. Subclasses implement the fetches, and pacing and retrying are shared
    here, so a second service is one module saying where its data comes from and how it names it.
    """

    name: str
    """How this source is named on the command line."""

    oldest_season: int
    """The oldest season this source exposes box scores for."""

    request_interval: float
    """Seconds to leave between two requests, which is what keeps a source from refusing to answer."""

    retries: int = 3
    retry_interval: float = 5

    def __init__(self, request_interval: float | None = None):
        if request_interval is not None:
            self.request_interval = request_interval

        self._next_request_time = 0.0
        self._progress_reporter: Callable[[str], None] | None = None

    def set_progress_reporter(self, reporter: Callable[[str], None] | None):
        """Names where a long fetch can report its progress."""

        self._progress_reporter = reporter

    def _report_progress(self, message: str):
        if self._progress_reporter is not None:
            self._progress_reporter(message)

    def _pace_request(self):
        time.sleep(max(0.0, self._next_request_time - time.monotonic()))
        self._next_request_time = time.monotonic() + self.request_interval

    def _fetch(
        self,
        fetch: Callable[[], Fetched],
        description: str,
        pace: bool = True
        ) -> Fetched | None:
        """
        Runs one request against the service, waiting out the rate limit first and retrying a
        request that fails. Returns None once the retries are used up, so a long collection run
        carries on past a season the service will not answer for.
        """

        for attempt in range(self.retries):
            if pace:
                self._pace_request()

            try:
                return fetch()
            except (SourceAuthenticationError, SourceDataError):
                raise
            except Exception as error:
                print(f"Failed to fetch {description}, attempt {attempt + 1} of {self.retries}: {error}")
                time.sleep(self.retry_interval)

        return None

    def seasons(self, date_from: date | None = None, date_to: date | None = None) -> list[int]:
        """Every season this source covers that could hold a game inside the given dates."""

        first = self.oldest_season if date_from is None else season.season_of(date_from)
        last = season.current_season() if date_to is None else season.season_of(date_to)

        return list(range(max(first, self.oldest_season), min(last, season.current_season()) + 1))

    @abstractmethod
    def teams(self) -> list[Team]:
        """Every team, with the tricode that identifies it outside this service."""

        pass

    @abstractmethod
    def players(self) -> list[Player]:
        """Every player the source knows of, whether or not they are still active."""

        pass

    @abstractmethod
    def player_info(self, player_id: int) -> pd.DataFrame | None:
        """One row of a player's own information, named the way the player store holds it."""

        pass

    @abstractmethod
    def player_games(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> pd.DataFrame | None:
        """
        Every finished player box score of one season phase, named the way the player game store
        holds it. The dates narrow that down to games played inside them.
        """

        pass

    def player_game_batches(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> Iterable[pd.DataFrame | None]:
        """Yields player-game rows in independently storable batches.

        Sources that fetch a season in one response need only implement player_games().
        """

        games = self.player_games(season_year, season_type, date_from, date_to)
        if games is None:
            yield None
            return
        if not isinstance(games, pd.DataFrame) or games.empty or "GAME_ID" not in games:
            yield games
            return

        batch_parts: list[pd.DataFrame] = []
        batch_size = 0
        for game_id, game_rows in games.groupby("GAME_ID", sort=False, dropna=False):
            if len(game_rows) > PLAYER_GAME_BATCH_SIZE:
                raise SourceDataError(
                    f"Player game {game_id} has too many rows for one {PLAYER_GAME_BATCH_SIZE}-row batch."
                )
            if batch_size and batch_size + len(game_rows) > PLAYER_GAME_BATCH_SIZE:
                yield pd.concat(batch_parts, ignore_index=True)
                batch_parts = []
                batch_size = 0
            batch_parts.append(game_rows)
            batch_size += len(game_rows)

        if batch_parts:
            yield pd.concat(batch_parts, ignore_index=True)

    @abstractmethod
    def rosters(self) -> list[RosterEntry] | None:
        """
        Who is on each team right now, and who the injury report rules out.

        This is the only fetch that says who will play rather than who played. A service that
        publishes no roster or injury feed answers None, and the pipeline goes on assuming a team
        plays whoever played its last game. A fetch that should have worked and did not raises
        instead, so a broken feed is never read as a league with nobody on it.
        """

        pass

    @abstractmethod
    def schedule(self, season_year: int) -> list[ScheduledGame] | None:
        """
        Every game of one season, whether or not it has been played.

        This is the only fetch that returns games with no box score, and it is what tells the site
        which games are still to come. A game whose phase this project does not model, or whose two
        teams are not both decided yet, is left out.
        """

        pass
