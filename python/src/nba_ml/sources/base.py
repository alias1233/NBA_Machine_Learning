"""
What every NBA data source has to provide.

A source is the only part of the pipeline that talks to an outside service. It hands back rows and
identities named the way the stores hold them, so swapping one source for another changes nothing
downstream. Rate limiting and retrying live here too, because how fast a service may be asked and
how it fails are properties of that service and not of the code collecting from it.

Nothing here searches or reads. A source only fetches. Finding a player or a team by name is a
question about what is already stored, so it lives in the stores and needs no service at all.
"""

import time
from abc import ABC, abstractmethod
from datetime import date
from typing import Callable, TypeVar

import pandas as pd

from nba_ml import season
from nba_ml.entities import Player, Team
from nba_ml.season import SeasonType

Fetched = TypeVar("Fetched")

class DataSource(ABC):
    """
    One provider of NBA data.

    Subclasses implement the fetches. Pacing requests and retrying them are shared here, so a second
    service is one module that says where its data comes from and what its columns are called.
    """

    name: str
    """How this source is named on the command line."""

    oldest_season: int
    """The oldest season this source has complete box scores for."""

    request_interval: float
    """Seconds to leave between two requests, which is what keeps a source from refusing to answer."""

    retries: int = 3
    retry_interval: float = 5

    def __init__(self, request_interval: float | None = None):
        if request_interval is not None:
            self.request_interval = request_interval

        self._next_request_time = 0.0

    def _fetch(self, fetch: Callable[[], Fetched], description: str) -> Fetched | None:
        """
        Runs one request against the service, waiting out the rate limit first and retrying a
        request that fails. Returns None once the retries are used up, so a long collection run
        carries on past a season the service will not answer for.
        """

        for attempt in range(self.retries):
            time.sleep(max(0.0, self._next_request_time - time.monotonic()))
            self._next_request_time = time.monotonic() + self.request_interval

            try:
                return fetch()
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

    @abstractmethod
    def team_games(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> pd.DataFrame | None:
        """The same as player_games, one row per team per game instead of per player."""

        pass
