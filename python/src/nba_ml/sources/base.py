"""Base class that every NBA data source implements."""

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
    """Raised when the source rejects the API key or the account tier can't use the endpoint."""

class SourceDataError(RuntimeError):
    """Raised when the source returns data that is not safe to store."""

class DataSource(ABC):
    """A provider of NBA data."""

    name: str
    """Name used to select this source on the command line."""

    oldest_season: int
    """Oldest season this source has box scores for."""

    request_interval: float
    """Seconds to wait between requests."""

    retries: int = 3
    retry_interval: float = 5

    def __init__(self, request_interval: float | None = None):
        if request_interval is not None:
            self.request_interval = request_interval

        self._next_request_time = 0.0
        self._progress_reporter: Callable[[str], None] | None = None

    def set_progress_reporter(self, reporter: Callable[[str], None] | None):
        """Sets the function that long fetches call to report progress."""

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
        """Runs a request with rate limiting and retries. Returns None if every retry fails."""

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
        """Returns the seasons this source covers that overlap the given dates."""

        first = self.oldest_season if date_from is None else season.season_of(date_from)
        last = season.current_season() if date_to is None else season.season_of(date_to)

        return list(range(max(first, self.oldest_season), min(last, season.current_season()) + 1))

    @abstractmethod
    def teams(self) -> list[Team]:
        """Returns every team with its abbreviation."""

        pass

    @abstractmethod
    def players(self) -> list[Player]:
        """Returns every player the source has, active or not."""

        pass

    @abstractmethod
    def player_info(self, player_id: int) -> pd.DataFrame | None:
        """Returns one row of player info, with the same column names as the player store."""

        pass

    @abstractmethod
    def player_games(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> pd.DataFrame | None:
        """Returns the finished player box scores of one season and season type within the given dates."""

        pass

    def player_game_batches(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> Iterable[pd.DataFrame | None]:
        """Yields player game rows in batches that can each be stored on their own."""

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
        """Returns the current rosters, or None if the source has no roster data."""

        pass

    @abstractmethod
    def schedule(self, season_year: int) -> list[ScheduledGame] | None:
        """Returns every game of a season, played or not."""

        pass
