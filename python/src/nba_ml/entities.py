"""Core data classes: players, teams, games and rosters."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Iterable

from nba_ml.season import SeasonType

@dataclass(frozen=True)
class Player():
    id: int
    name: str

@dataclass(frozen=True)
class Team():
    id: int
    name: str
    abbreviation: str
    """Three-letter team code, e.g. LAL."""

@dataclass(frozen=True)
class Game():
    """A game and the details known before it is played."""

    date: date
    home_team_id: int
    away_team_id: int
    season_type: SeasonType = SeasonType.REGULAR_SEASON

    @property
    def team_ids(self) -> tuple[int, int]:
        """Both team IDs, home team first."""

        return (self.home_team_id, self.away_team_id)

    def opponent_of(self, team_id: int) -> int:
        if team_id == self.home_team_id:
            return self.away_team_id

        if team_id == self.away_team_id:
            return self.home_team_id

        raise ValueError(f"Team {team_id} is not playing in this game.")

    def is_home(self, team_id: int) -> bool:
        if team_id not in (self.home_team_id, self.away_team_id):
            raise ValueError(f"Team {team_id} is not playing in this game.")

        return team_id == self.home_team_id

@dataclass(frozen=True)
class RosterScenario():
    """Changes to a team's lineup compared to its last game."""

    without: frozenset[int] = frozenset()
    """Core players from the team's last game who will not play in this one."""

    returning: frozenset[int] = frozenset()
    """Players expected to play who missed the team's last game."""

    @staticmethod
    def of(without: Iterable[int] = (), returning: Iterable[int] = ()) -> "RosterScenario":
        return RosterScenario(frozenset(without), frozenset(returning))

NOT_PLAYING_STATUSES = frozenset({"out", "doubtful"})
"""Injury statuses that count as not playing."""

@dataclass(frozen=True)
class RosterEntry():
    """A player's current team and injury status, as reported by the data source."""

    player_id: int
    team_id: int
    status: str | None = None
    """Injury status exactly as the injury report gives it."""

    @property
    def playing(self) -> bool:
        return self.status is None or self.status.strip().lower() not in NOT_PLAYING_STATUSES

class GameStatus(Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINAL = "FINAL"

@dataclass(frozen=True)
class ScheduledGame():
    """A game on the schedule, whether or not it has been played."""

    id: int
    game: Game
    status: GameStatus
    tipoff: datetime | None = None
    is_mock: bool = False
    """True for games added manually for testing."""

    @property
    def team_ids(self) -> tuple[int, int]:
        return self.game.team_ids
