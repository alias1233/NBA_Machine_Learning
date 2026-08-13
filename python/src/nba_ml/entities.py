"""
The things this project talks about: a player, a team, and one game.

These are named in our own vocabulary rather than any data service's, so an endpoint, a command and a
store all speak the same one. A source translates its own shapes into these on the way in.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

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
    """The three letter tricode, such as LAL. Every service publishes it and it does not change."""

@dataclass(frozen=True)
class Game():
    """
    One game, described by what is known before it is played.

    Naming the two teams rather than a team, an opponent and a home flag means a caller cannot
    describe a game that could not happen. Which side a player is on follows from which team they
    play for.
    """

    date: date
    home_team_id: int
    away_team_id: int
    season_type: SeasonType = SeasonType.REGULAR_SEASON

    @property
    def team_ids(self) -> tuple[int, int]:
        """Both sides, the home team first."""

        return (self.home_team_id, self.away_team_id)

    def opponent_of(self, team_id: int) -> int:
        if team_id == self.home_team_id:
            return self.away_team_id

        if team_id == self.away_team_id:
            return self.home_team_id

        raise ValueError(f"Team {team_id} is not playing in this game.")

    def is_home(self, team_id: int) -> bool:
        """
        Raises:
            ValueError if the team is not playing in this game, so a wrong team is never read as away.
        """

        if team_id not in (self.home_team_id, self.away_team_id):
            raise ValueError(f"Team {team_id} is not playing in this game.")

        return team_id == self.home_team_id

class GameStatus(Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINAL = "FINAL"

@dataclass(frozen=True)
class ScheduledGame():
    """
    One game on the published schedule, played or not.

    A Game says what a prediction needs. This adds what the schedule itself carries: the id the game
    is published under, how far along it is, and when it starts.
    """

    id: int
    game: Game
    status: GameStatus
    tipoff: datetime | None = None
    is_mock: bool = False
    """Added by hand for testing rather than fetched. See nba_ml/cli/schedule.py."""

    @property
    def team_ids(self) -> tuple[int, int]:
        return self.game.team_ids
