"""
The prediction service.

The endpoints here are the ones no model family owns: the teams, the players, the games that can be
predicted, and the models that exist. They answer for every family from nba_ml/models/families.py,
so a new family is listed the moment it is added there.

Predicting is family specific, because what a request names differs, so each family brings its own
router under /predictions/<family>. Adding one is a module beside api/player_stats.py and a line in
FAMILY_ROUTERS.
"""

from datetime import date, datetime, timedelta

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from nba_ml import upcoming
from nba_ml.api import player_stats
from nba_ml.api.schemas import PlayerResponse, TeamResponse, team_id
from nba_ml.entities import ScheduledGame
from nba_ml.models.errors import PredictionRefused
from nba_ml.models.families import ALL_FAMILIES, ALL_MODEL_NAMES
from nba_ml.models.outputs import DISCRIMINATOR, ModelOutput
from nba_ml.season import SeasonType
from nba_ml.stores import player_games, players, teams

app = FastAPI(
    title="NBA Machine Learning",
    summary="Predicts NBA statistics before a game is played."
)

FAMILY_ROUTERS = [player_stats.router]

for family_router in FAMILY_ROUTERS:
    app.include_router(family_router)

# How far back a team's players are read from. Long enough that the answer survives an off season,
# since who last played for a team is the only roster this project holds.
ROSTER_WINDOW = timedelta(days=365)

# Answers
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

    predicts: list[str]
    """What the model answers about, in the words a reader sees."""

    output: ModelOutput = Field(discriminator=DISCRIMINATOR)
    """The shape of an answer, which is what tells a caller how to draw one."""

    published: bool
    """Whether a trained file exists, so a caller can offer the model without every request failing."""

class HealthResponse(BaseModel):
    models: list[str]
    newest_stored_game: date | None
    """A prediction reads rest off the gap to the player's last game, so stale data reads as a layoff."""

@app.exception_handler(PredictionRefused)
def _refused(request: Request, refusal: PredictionRefused) -> JSONResponse:
    """
    A request that is well formed and cannot be answered from what is stored.

    The reason travels beside the message so a caller can word the failure for its own reader rather
    than repeat a sentence naming stored ids.
    """

    return JSONResponse(
        status_code=422,
        content={"detail": {"reason": refusal.reason.value, "message": str(refusal)}}
    )

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
        models=ALL_MODEL_NAMES,
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

    player_ids = player_games.player_ids_on_team(team_id(abbreviation), date.today() - ROSTER_WINDOW)

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
    """
    Every model of every family, published or not.

    A model with no trained file is still listed, so a caller can say a family is coming without
    inventing one. Whether it can answer is the published flag.
    """

    return [
        ModelResponse(
            name=specification.name,
            family=family.name,
            predicts=list(specification.predicts),
            output=specification.output,
            published=family.is_published(specification)
        )
        for family in ALL_FAMILIES
        for specification in family.specifications.values()
    ]
