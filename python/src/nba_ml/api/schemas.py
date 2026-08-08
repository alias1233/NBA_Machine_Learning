"""
The pieces every family's endpoints share: the shapes that cross the wire and the lookup that turns
a name a caller sent into a stored id.

Every identifier a caller uses is one this project owns and stores: a player id, a team tricode such
as LAL, a model name, and a season phase. None of them come from a data service, so a change of
service cannot break a saved link.

A game is named by its date and its two teams rather than by a team, an opponent and a home flag,
which means a caller cannot describe a game that could not happen.
"""

from datetime import date

from fastapi import HTTPException
from pydantic import BaseModel

from nba_ml.entities import Game
from nba_ml.season import SeasonType
from nba_ml.stores import teams

class TeamResponse(BaseModel):
    abbreviation: str
    name: str

class PlayerResponse(BaseModel):
    id: int
    name: str

class PredictionResponse(BaseModel):
    """
    One answer, whatever family produced it.

    It is a probability for every whole number outcome, counting up from minimum_value. Expected
    value and the odds for a line are sums over that array, which the caller does on its own.
    """

    model: str
    minimum_value: int
    probabilities: list[float]

class GameRequest(BaseModel):
    date: date
    home_team: str
    """A tricode such as LAL, or a full team name."""

    away_team: str
    season_type: SeasonType = SeasonType.REGULAR_SEASON

    def to_game(self) -> Game:
        return Game(self.date, team_id(self.home_team), team_id(self.away_team), self.season_type)

def team_id(abbreviation_or_name: str) -> int:
    team = teams.find(abbreviation_or_name)
    if team is None:
        raise HTTPException(404, f"No stored team matches {abbreviation_or_name}.")

    return team.id
