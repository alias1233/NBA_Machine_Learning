"""
The prediction service.

Every identifier a caller uses is one this project owns and stores: a player id, a team tricode such
as LAL, a model name, and a season phase. None of them come from a data service, so a change of
service cannot break a saved link.

A game is named by its date and its two teams rather than by a team, an opponent and a home flag,
which means a caller cannot describe a game that could not happen.

The answer is a probability for every whole number outcome. Over and under odds for any line are the
sum of the probabilities past it, which the browser does on its own.
"""

from datetime import date, datetime, timedelta

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from nba_ml import upcoming
from nba_ml.entities import Game, ScheduledGame
from nba_ml.models.player_stats import inference, odds, specifications
from nba_ml.season import SeasonType
from nba_ml.stores import player_games, players, teams

app = FastAPI(
    title="NBA Machine Learning",
    summary="Predicts the probability of every whole number outcome of a player's stat in one game."
)

# How far back a team's players are read from. Long enough that the answer survives an off season,
# since who last played for a team is the only roster this project holds.
ROSTER_WINDOW = timedelta(days=365)

# Answers
class TeamResponse(BaseModel):
    abbreviation: str
    name: str

class PlayerResponse(BaseModel):
    id: int
    name: str

class ScheduledGameResponse(BaseModel):
    """One upcoming game that can be predicted right now."""

    id: int
    date: date
    tipoff: datetime | None
    """When the game starts, in UTC. Null when the schedule does not name a time."""

    home_team: TeamResponse
    away_team: TeamResponse
    season_type: SeasonType
    is_mock: bool
    """Added by hand for testing rather than collected, so a page can say so."""

class ModelResponse(BaseModel):
    name: str
    """What to pass as the model in a prediction request."""

    family: str
    """Which group of models this belongs to, which is the page it is predicted on."""

    stats: list[str]
    minimum_value: int
    """The value the first probability stands for."""

    outcomes: int
    published: bool
    """Whether a trained file exists, so a caller can offer the model without every request failing."""

class HealthResponse(BaseModel):
    models: list[str]
    newest_stored_game: date | None
    """A prediction reads rest off the gap to the player's last game, so stale data reads as a layoff."""

class PredictionResponse(BaseModel):
    model: str
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

class PredictionRequest(BaseModel):
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

def _scheduled_game_response(
    scheduled: ScheduledGame,
    named_teams: dict[int, TeamResponse]
    ) -> ScheduledGameResponse:
    return ScheduledGameResponse(
        id=scheduled.id,
        date=scheduled.game.date,
        tipoff=scheduled.tipoff,
        home_team=named_teams[scheduled.game.home_team_id],
        away_team=named_teams[scheduled.game.away_team_id],
        season_type=scheduled.game.season_type,
        is_mock=scheduled.is_mock
    )

@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(
        models=specifications.MODEL_NAMES,
        newest_stored_game=player_games.latest_game_date()
    )

@app.get("/teams")
def all_teams() -> list[TeamResponse]:
    return [
        TeamResponse(abbreviation=team.abbreviation, name=team.name)
        for team in sorted(teams.all_teams(), key=lambda team: team.abbreviation)
    ]

@app.get("/teams/{abbreviation}/players")
def team_players(abbreviation: str) -> list[PlayerResponse]:
    """
    Who plays for a team, taken as everyone whose most recent game in the last year was for it.

    This is what fills the player list once a game has been chosen. There is no roster feed, so a
    player traded in the off season stays on their old team until they play for the new one.
    """

    player_ids = player_games.player_ids_on_team(_team_id(abbreviation), date.today() - ROSTER_WINDOW)

    return [
        PlayerResponse(id=player.id, name=player.name)
        for player in sorted(players.get_players(player_ids), key=lambda player: player.name)
    ]

@app.get("/games/upcoming")
def upcoming_games() -> list[ScheduledGameResponse]:
    """
    The games that can be predicted right now, soonest first.

    A game is left out until every earlier game of both its teams has been collected, because until
    then the model would read one of them as a game out of date. See nba_ml/upcoming.py.
    """

    named_teams = {
        team.id: TeamResponse(abbreviation=team.abbreviation, name=team.name)
        for team in teams.all_teams()
    }

    return [_scheduled_game_response(scheduled, named_teams) for scheduled in upcoming.predictable_games()]

@app.get("/players")
def find_players(
    search: str = Query(min_length=2, description="Part of a player's name. Accents are ignored."),
    limit: int = Query(default=10, ge=1, le=100)
    ) -> list[PlayerResponse]:
    return [
        PlayerResponse(id=player.id, name=player.name)
        for player in players.find_by_name(search, limit)
    ]

@app.get("/players/{player_id}")
def get_player(player_id: int) -> PlayerResponse:
    """Names a player from a stored id, so a saved prediction link reads without a search."""

    player = players.get_player(player_id)
    if player is None:
        raise HTTPException(404, f"No stored player has the id {player_id}.")

    return PlayerResponse(id=player.id, name=player.name)

@app.get("/models")
def all_models() -> list[ModelResponse]:
    return [
        ModelResponse(
            name=specification.name,
            family=specifications.MODEL_CATEGORY,
            stats=[stat.name.lower() for stat in specification.target_stats],
            minimum_value=specification.minimum_of_stat,
            outcomes=specification.number_of_stat_classifications,
            published=inference.can_load(specification)
        )
        for specification in specifications.ALL_MODEL_SPECIFICATIONS.values()
    ]

@app.post("/predictions/player-stats/{model}")
def predict_player_stat(model: str, request: PredictionRequest) -> PredictionResponse:
    specification = specifications.ALL_MODEL_SPECIFICATIONS.get(model)
    if specification is None:
        raise HTTPException(404, f"No model is named {model}. See /models.")

    if players.get_player(request.player_id) is None:
        raise HTTPException(404, f"No stored player has the id {request.player_id}.")

    if not inference.can_load(specification):
        raise HTTPException(503, f"The {specification.name} model has no published file yet.")

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

    return PredictionResponse(
        model=specification.name,
        minimum_value=specification.minimum_of_stat,
        probabilities=probabilities,
        expected_value=odds.expected_value(probabilities, specification.minimum_of_stat)
    )
