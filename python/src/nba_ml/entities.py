"""
The things this project talks about: a player, a team, and one game.

These are named in our own vocabulary rather than any data service's, so they are what an endpoint,
a command and a store all speak. A source translates its own shapes into these on the way in, which
is what keeps a change of service from reaching anything downstream.
"""

from dataclasses import dataclass
from datetime import date

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

    def opponent_of(self, team_id: int) -> int:
        if team_id == self.home_team_id:
            return self.away_team_id

        if team_id == self.away_team_id:
            return self.home_team_id

        raise ValueError(f"Team {team_id} is not playing in this game.")

    def is_home(self, team_id: int) -> bool:
        self.opponent_of(team_id)

        return team_id == self.home_team_id
