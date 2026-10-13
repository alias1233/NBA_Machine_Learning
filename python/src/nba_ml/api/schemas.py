"""Request and response models shared by the prediction endpoints, plus the team ID lookup."""

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
    """Response for a prediction from any model family."""

    model: str
    output: ModelOutput = Field(discriminator=DISCRIMINATOR)
    values: list[float]

    past_games: int
    """Number of past games the prediction was based on."""

class ScenarioRequest(BaseModel):
    """Changes to one team's lineup compared to its last game."""

    without: list[int] = Field(default_factory=list)
    returning: list[int] = Field(default_factory=list)

    def to_scenario(self) -> RosterScenario:
        return RosterScenario.of(self.without, self.returning)

class GameRostersRequest(BaseModel):
    home: ScenarioRequest = Field(default_factory=ScenarioRequest)
    away: ScenarioRequest = Field(default_factory=ScenarioRequest)

    def to_scenarios(self, game: Game) -> dict[int, RosterScenario]:
        return {
            game.home_team_id: self.home.to_scenario(),
            game.away_team_id: self.away.to_scenario()
        }

class GameRequest(BaseModel):
    date: date
    home_team: str
    """Team abbreviation (e.g. LAL) or full team name."""

    away_team: str
    season_type: SeasonType = SeasonType.REGULAR_SEASON

    def to_game(self) -> Game:
        return Game(self.date, team_id(self.home_team), team_id(self.away_team), self.season_type)

def team_id(abbreviation_or_name: str) -> int:
    team = teams.find(abbreviation_or_name)
    if team is None:
        raise HTTPException(404, f"No stored team matches {abbreviation_or_name}.")

    return team.id
