"""
The pieces every family's endpoints share: the shapes that cross the wire and the lookup that turns
a name a caller sent into a stored id.

Every identifier a caller uses is one this project owns and stores: a player id, a team tricode such
as LAL, a model name, and a season phase. None of them come from a data service, so a change of
service cannot break a saved link.
"""

from datetime import date

from fastapi import HTTPException
from pydantic import BaseModel, Field

from nba_ml.entities import Game, RosterScenario
from nba_ml.models.outputs import DISCRIMINATOR, ModelOutput
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

    The output says what each value stands for. Anything read off them, such as the expected value or
    the odds for a line, is arithmetic the caller already holds everything for.
    """

    model: str
    output: ModelOutput = Field(discriminator=DISCRIMINATOR)
    values: list[float]

    past_games: int
    """How many earlier games the answer was built from, so a caller can say it rests on very little."""

class ScenarioRequest(BaseModel):
    """
    Which core players take the floor for one team, where that differs from its last game.

    Nothing collected says who will play, so a team plays whoever played its last game unless a
    request says otherwise. Both lists are stored player ids.
    """

    without: list[int] = Field(default_factory=list)
    returning: list[int] = Field(default_factory=list)

    def to_scenario(self) -> RosterScenario:
        return RosterScenario.of(self.without, self.returning)

class GameRostersRequest(BaseModel):
    """
    The roster change each side of a game is making, named by which side it is.

    Both sides are read by every model built on team game rows, because one row carries what the team
    it faces has available as well as its own.
    """

    home: ScenarioRequest = Field(default_factory=ScenarioRequest)
    away: ScenarioRequest = Field(default_factory=ScenarioRequest)

    def to_scenarios(self, game: Game) -> dict[int, RosterScenario]:
        """The same change keyed by team id, which is how a build asks for it."""

        return {
            game.home_team_id: self.home.to_scenario(),
            game.away_team_id: self.away.to_scenario()
        }

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
