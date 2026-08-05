"""
The prediction service.

Every identifier a caller uses is one this project owns and stores: a player id, a team tricode such
as LAL, a stat name, and a season phase. None of them come from a data service, so the browser never
has to know which service the data was collected from and a change of service cannot break a saved
link.

A game is named by its date and its two teams rather than by a team, an opponent and a home flag,
which means a caller cannot describe a game that could not happen. Once the schedule is stored, a
stored game id becomes a second way to say the same thing.

The answer is a probability for every whole number outcome. Over and under odds for any line are the
sum of the probabilities past it, which the browser does on its own.
"""

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from nba_ml.entities import Game
from nba_ml.models.player_stats import inference, specifications
from nba_ml.season import SeasonType
from nba_ml.stores import player_games, players, teams

app = FastAPI(
    title="NBA Machine Learning",
    summary="Predicts the probability of every whole number outcome of a player's stat in one game."
)

# Answers
class TeamResponse(BaseModel):
    abbreviation: str
    name: str

class PlayerResponse(BaseModel):
    id: int
    name: str

class StatModelResponse(BaseModel):
    stat: str
    minimum_value: int
    """The value the first probability stands for."""

    outcomes: int

class HealthResponse(BaseModel):
    stats: list[str]
    newest_stored_game: date | None
    """A prediction reads rest off the gap to the player's last game, so stale data reads as a layoff."""

class PlayerPropResponse(BaseModel):
    stat: str
    minimum_value: int
    probabilities: list[float]
    expected_value: float

# Requests
class GameRequest(BaseModel):
    date: date
    home_team: str
    """A tricode such as LAL, or a full team name."""

    away_team: str
    season_type: SeasonType = SeasonType.REGULAR_SEASON

class ScenarioRequest(BaseModel):
    """Which core players are on the floor, when that differs from the team's last game."""

    without: list[int] = Field(default_factory=list)
    returning: list[int] = Field(default_factory=list)

class PlayerPropRequest(BaseModel):
    player_id: int
    game: GameRequest
    player_team: str | None = None
    """Only needed when the player has just moved and no game records it yet."""

    scenario: ScenarioRequest = Field(default_factory=ScenarioRequest)

def _team_id(abbreviation_or_name: str) -> int:
    team = teams.find(abbreviation_or_name)
    if team is None:
        raise HTTPException(404, f"No stored team matches {abbreviation_or_name}.")

    return team.id

@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(
        stats=sorted(specifications.ALL_MODEL_SPECIFICATIONS),
        newest_stored_game=player_games.latest_game_date()
    )

@app.get("/teams")
def all_teams() -> list[TeamResponse]:
    return [
        TeamResponse(abbreviation=team.abbreviation, name=team.name)
        for team in sorted(teams.all_teams(), key=lambda team: team.abbreviation)
    ]

@app.get("/players")
def find_players(
    search: str = Query(min_length=2, description="Part of a player's name. Accents are ignored."),
    limit: int = Query(default=10, ge=1, le=100)
    ) -> list[PlayerResponse]:
    return [
        PlayerResponse(id=player.id, name=player.name)
        for player in players.find_by_name(search, limit)
    ]

@app.get("/stat-models")
def all_stat_models() -> list[StatModelResponse]:
    return [
        StatModelResponse(
            stat=specification.name,
            minimum_value=specification.minimum_of_stat,
            outcomes=specification.number_of_stat_classifications
        )
        for specification in specifications.ALL_MODEL_SPECIFICATIONS.values()
    ]

@app.post("/predictions/player-props/{stat}")
def predict_player_prop(stat: str, request: PlayerPropRequest) -> PlayerPropResponse:
    specification = specifications.ALL_MODEL_SPECIFICATIONS.get(stat)
    if specification is None:
        raise HTTPException(404, f"No model predicts {stat}. See /stat-models.")

    if players.get_player(request.player_id) is None:
        raise HTTPException(404, f"No stored player has the id {request.player_id}.")

    game = Game(
        request.game.date,
        _team_id(request.game.home_team),
        _team_id(request.game.away_team),
        request.game.season_type
    )

    try:
        probabilities = inference.predict(
            specification,
            request.player_id,
            game,
            set(request.scenario.without),
            set(request.scenario.returning),
            target_player_team_id=None if request.player_team is None else _team_id(request.player_team),
            print_debug=False
        )
    except ValueError as error:
        raise HTTPException(422, str(error))

    return PlayerPropResponse(
        stat=specification.name,
        minimum_value=specification.minimum_of_stat,
        probabilities=probabilities,
        expected_value=sum(
            (specification.minimum_of_stat + offset) * probability
            for offset, probability in enumerate(probabilities)
        )
    )
