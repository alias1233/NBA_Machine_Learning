"""FastAPI app for the prediction API, plus the endpoints shared by all model families."""

from datetime import date, datetime, timedelta
from typing import Collection

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from nba_ml import expected_rosters, season, showcase, upcoming
from nba_ml.api import game_stats, limits, player_stats, team_stats
from nba_ml.api.schemas import PlayerResponse, TeamResponse
from nba_ml.entities import Game, ScheduledGame, Team
from nba_ml.feature_engineering import feature_store
from nba_ml.models.errors import PredictionRefused
from nba_ml.models import metrics
from nba_ml.models.families import ALL_FAMILIES, ALL_MODEL_NAMES
from nba_ml.models.outputs import DISCRIMINATOR, ModelOutput
from nba_ml.models.player_stats import features as player_stat_features
from nba_ml.models.specifications import GameSide, ModelSpecification
from nba_ml.season import SeasonType
from nba_ml.stores import player_games, players, rosters, schedule, team_games, teams

app = FastAPI(
    title="NBA Machine Learning",
    summary="Predicts NBA statistics before a game is played."
)

FAMILY_ROUTERS = [player_stats.router, team_stats.router, game_stats.router]

for family_router in FAMILY_ROUTERS:
    app.include_router(family_router, dependencies=[Depends(limits.prediction_slot)])

# How far back to look for players who played for a team.
ROSTER_WINDOW = timedelta(days=365)

# Teams with no games in this window are left out of /teams.
ACTIVE_TEAM_WINDOW = timedelta(days=365)

# Response models
class ScheduledGameResponse(BaseModel):
    id: int
    date: date
    tipoff: datetime | None
    """Start time in UTC. Null if the schedule has no time for the game yet."""

    home_team: TeamResponse
    away_team: TeamResponse
    season_type: SeasonType
    is_mock: bool
    """True for games added manually for testing."""

class RosterResponse(BaseModel):
    team: TeamResponse
    players: list[PlayerResponse]
    """The team's projected roster, including players who missed its last game."""

    without: list[PlayerResponse]
    """Players from the team's last game who are not expected to play in this one."""

    returning: list[PlayerResponse]
    """Players expected to play in this game who missed the team's last one."""

class ModelResponse(BaseModel):
    name: str
    """The model name to use in a prediction request."""

    title: str

    description: str

    family: str

    predicts: list[str]

    output: ModelOutput = Field(discriminator=DISCRIMINATOR)

    read_from: GameSide | None
    """For signed outputs such as point differential, the team a positive value belongs to."""

    category_sides: list[GameSide] | None
    """The team each output category refers to, in the same order as the categories."""

    published: bool
    """True if the model has a trained file that can be loaded."""

class MetricResponse(BaseModel):
    key: str

    label: str
    value: float
    floor: float | None
    """The same metric for a baseline that predicts the outcome frequencies seen in training."""

    unit: metrics.MetricUnit

    higher_is_better: bool

    ideal: float | None
    """Target value for metrics where closer to it is better."""

class MetricDefinitionResponse(BaseModel):
    key: str
    label: str
    description: str

class ModelEvaluationResponse(BaseModel):
    """A model's metrics on held-out games."""

    scored_on: str

    samples: int
    first_game: date
    last_game: date

    evaluated: datetime
    metrics: list[MetricResponse]
    """The metrics shown for this model, most important first."""

class InfoModelResponse(BaseModel):
    """A model as listed on its family page, with its title, description and metrics."""

    name: str

    title: str

    description: str

    published: bool

    evaluation: ModelEvaluationResponse | None

class HealthResponse(BaseModel):
    models: list[str]
    newest_stored_game: date | None

    feature_build: str | None
    """Version of the feature build currently used for player predictions."""

    roster_snapshot: datetime | None
    """When the stored roster and injury snapshot was collected, in UTC."""

@app.exception_handler(PredictionRefused)
def _refused(request: Request, refusal: PredictionRefused) -> JSONResponse:
    """Returns a 422 when a valid request can't be answered with the stored data."""

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
    build = feature_store.current(player_stat_features.BUILD_NAME)

    return HealthResponse(
        models=ALL_MODEL_NAMES,
        newest_stored_game=player_games.latest_game_date(),
        feature_build=None if build is None else build.version,
        roster_snapshot=rosters.collected_at()
    )

@app.get("/showcase")
def todays_showcase() -> dict | None:
    """Returns the sample predictions shown on the home page."""

    return showcase.read()

@app.get("/teams")
def all_teams() -> list[TeamResponse]:
    """Returns all active teams, one per abbreviation, sorted by abbreviation."""

    newest = team_games.latest_game_date()
    playing = (
        set() if newest is None
        else team_games.team_ids_with_game_since(newest - ACTIVE_TEAM_WINDOW)
    )

    named: dict[str, str] = {}

    for team in teams.all_teams():
        if team.id in playing:
            named.setdefault(team.abbreviation, team.name)

    return [
        TeamResponse(abbreviation=abbreviation, name=named[abbreviation])
        for abbreviation in sorted(named)
    ]

def _named(player_ids: Collection[int]) -> list[PlayerResponse]:
    """Returns the given players that have a name, sorted by name."""

    return [
        PlayerResponse(id=player.id, name=player.name)
        for player in sorted(players.get_players(player_ids), key=lambda player: player.name)
    ]

def _roster(team: Team, game: Game) -> RosterResponse:
    played_for = player_games.player_ids_on_team(team.id, season.today() - ROSTER_WINDOW)
    on_team_now = {entry.player_id for entry in rosters.on_team(team.id)}
    moved_on = {
        player_id
        for player_id, entry in rosters.entries_for(played_for).items()
        if entry.team_id != team.id
    }
    expected = expected_rosters.expected_scenario(team.id, game.date)

    return RosterResponse(
        team=TeamResponse(abbreviation=team.abbreviation, name=team.name),
        players=_named(on_team_now | (set(played_for) - moved_on)),
        without=_named(expected.without),
        returning=_named(expected.returning)
    )

@app.get("/games/{game_id}/rosters")
def game_rosters(game_id: int) -> list[RosterResponse]:
    """Returns both teams' rosters for a scheduled game, away team first."""

    scheduled = schedule.get_game(game_id)
    if scheduled is None:
        raise HTTPException(404, f"No scheduled game has the id {game_id}.")

    named_teams = {team.id: team for team in teams.all_teams()}
    missing = [
        side for side in scheduled.game.team_ids if side not in named_teams
    ]
    if missing:
        raise HTTPException(404, f"No stored team has the id {missing[0]}.")

    return [
        _roster(named_teams[side], scheduled.game)
        for side in (scheduled.game.away_team_id, scheduled.game.home_team_id)
    ]

@app.get("/games/upcoming")
def upcoming_games() -> list[ScheduledGameResponse]:
    """Returns the upcoming games that can be predicted right now, earliest first."""

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
    """Returns the player with the given ID."""

    player = players.get_player(player_id)
    if player is None:
        raise HTTPException(404, f"No stored player has the id {player_id}.")

    return PlayerResponse(id=player.id, name=player.name)

@app.get("/models")
def all_models() -> list[ModelResponse]:
    """Returns all models from all families, including ones without a trained file."""

    return [
        ModelResponse(
            name=specification.name,
            title=specification.title,
            description=specification.description,
            family=family.name,
            predicts=list(specification.predicts),
            output=specification.output,
            read_from=specification.read_from,
            category_sides=(
                list(specification.category_sides) if specification.category_sides else None
            ),
            published=family.is_published(specification)
        )
        for family in ALL_FAMILIES
        for specification in family.specifications.values()
    ]

def _model_evaluation(specification: ModelSpecification) -> ModelEvaluationResponse | None:
    scored = metrics.read(specification.evaluation_file())
    if scored is None:
        return None

    shown = [
        MetricResponse(
            key=key,
            label=metrics.ALL_METRICS[key].label,
            value=scored.metrics[key],
            floor=scored.floor.get(key),
            unit=metrics.ALL_METRICS[key].unit,
            higher_is_better=metrics.ALL_METRICS[key].higher_is_better,
            ideal=metrics.ALL_METRICS[key].ideal
        )
        for key in specification.reported_metrics
        if key in scored.metrics and key in metrics.ALL_METRICS
    ]

    if not shown:
        return None

    return ModelEvaluationResponse(
        scored_on=scored.scored_on,
        samples=scored.samples,
        first_game=date.fromisoformat(scored.first_game),
        last_game=date.fromisoformat(scored.last_game),
        evaluated=datetime.fromisoformat(scored.evaluated),
        metrics=shown
    )

def _family(family: str):
    """Returns the model family with the given name, or raises a 404."""

    requested = next((candidate for candidate in ALL_FAMILIES if candidate.name == family), None)
    if requested is None:
        raise HTTPException(404, f"No model family is named {family}.")

    return requested

@app.get("/models/metrics")
def model_metric_definitions() -> list[MetricDefinitionResponse]:
    """Returns the label and description of every metric the models report."""

    used = dict.fromkeys(
        key
        for family in ALL_FAMILIES
        for specification in family.specifications.values()
        for key in specification.reported_metrics
        if key in metrics.ALL_METRICS
    )

    return [
        MetricDefinitionResponse(
            key=key,
            label=metrics.ALL_METRICS[key].label,
            description=metrics.ALL_METRICS[key].description
        )
        for key in used
    ]

@app.get("/models/{family}/info")
def family_info_models(family: str) -> list[InfoModelResponse]:
    """Returns the models in a family with their descriptions and evaluation metrics."""

    requested = _family(family)

    return [
        InfoModelResponse(
            name=specification.name,
            title=specification.title,
            description=specification.description,
            published=requested.is_published(specification),
            evaluation=_model_evaluation(specification)
        )
        for specification in requested.specifications.values()
    ]
