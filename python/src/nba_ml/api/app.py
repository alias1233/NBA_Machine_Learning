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

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from nba_ml import season, upcoming
from nba_ml.api import game_stats, limits, player_stats, team_stats
from nba_ml.api.schemas import PlayerResponse, TeamResponse, team_id
from nba_ml.entities import ScheduledGame
from nba_ml.feature_engineering import feature_store
from nba_ml.models.errors import PredictionRefused
from nba_ml.models import metrics
from nba_ml.models.families import ALL_FAMILIES, ALL_MODEL_NAMES
from nba_ml.models.outputs import DISCRIMINATOR, ModelOutput
from nba_ml.models.player_stats import features as player_stat_features
from nba_ml.models.specifications import GameSide, ModelSpecification
from nba_ml.season import SeasonType
from nba_ml.stores import player_games, players, team_games, teams

app = FastAPI(
    title="NBA Machine Learning",
    summary="Predicts NBA statistics before a game is played."
)

FAMILY_ROUTERS = [player_stats.router, team_stats.router, game_stats.router]

# Every prediction is capped here rather than in each family, because how many run at once is a
# property of the server rather than of the model. See nba_ml/api/limits.py.
for family_router in FAMILY_ROUTERS:
    app.include_router(family_router, dependencies=[Depends(limits.prediction_slot)])

# How far back a team's players are read from. Long enough that the answer survives an off season,
# since who last played for a team is the only roster this project holds.
ROSTER_WINDOW = timedelta(days=365)

# How recently a team has to have played to be offered as a side of a game. Measured back from the
# newest game held rather than from today, so an archive that has fallen behind still names thirty
# teams instead of none. A year covers an off season, which is the longest gap in the calendar.
ACTIVE_TEAM_WINDOW = timedelta(days=365)

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
    """
    Which group of models this belongs to, which is the page it is predicted on.

    A family is named after what a request has to name to get an answer: a player, a team, or a game.
    """

    predicts: list[str]
    """What the model answers about, in the words a reader sees."""

    output: ModelOutput = Field(discriminator=DISCRIMINATOR)
    """The shape of an answer, which is what tells a caller how to draw one."""

    read_from: GameSide | None
    """
    Which side of the game a value above zero belongs to, for an answer with a direction.

    Null where the answer names no side. A caller drawing one says whose number it is, because
    nothing else in a game statistic's answer marks which of the two teams it is about.
    """

    category_sides: list[GameSide] | None
    """
    Which side of the game each category names, in the order the output lists them.

    Null where no category names one. A name leads with its side's word, so a caller holding the
    game can put the team playing it in place of that word.
    """

    published: bool
    """Whether a trained file exists, so a caller can offer the model without every request failing."""

class MetricResponse(BaseModel):
    """One measured figure, with everything a caller needs to write it down and read it."""

    key: str
    """The stable name of the figure, so a caller can single one out without matching on wording."""

    label: str
    description: str
    """One sentence saying what the figure means, for a reader who knows nothing about the model."""

    value: float
    floor: float | None
    """
    What answering with the season's own spread of outcomes scores on the same games.

    Null where that floor cannot be scored on this figure. A caller showing one says what it is, so
    a reader can see what the model is worth rather than only what it scored.
    """

    unit: metrics.MetricUnit
    """How to write the number: an amount in the statistic's own units, a probability, or a score."""

    higher_is_better: bool

class ModelEvaluationResponse(BaseModel):
    """How one model scored on games it never saw while it was being fitted."""

    scored_on: str
    """Which split produced these figures. Only a held-out one is published."""

    samples: int
    first_game: date
    last_game: date
    """The stretch of calendar the scored games cover."""

    evaluated: datetime
    metrics: list[MetricResponse]
    """The figures this model chose to publish, headline first."""

class AboutModelResponse(BaseModel):
    """The model copy a family About page reads, separate from the prediction-page catalogue."""

    name: str
    """The stable model identifier."""

    title: str
    """The short reader-facing name."""

    description: str
    """The short reader-facing explanation."""

    published: bool
    """Whether a trained file exists."""

class HealthResponse(BaseModel):
    models: list[str]
    newest_stored_game: date | None
    """A prediction reads rest off the gap to the player's last game, so stale data reads as a layoff."""

    feature_build: str | None
    """
    Which whole-league feature build a player prediction is being answered from.

    Null while none has been published, which is what makes every player request build the league for
    itself. See nba_ml/cli/build_features.py.
    """

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
    build = feature_store.current(player_stat_features.BUILD_NAME)

    return HealthResponse(
        models=ALL_MODEL_NAMES,
        newest_stored_game=player_games.latest_game_date(),
        feature_build=None if build is None else build.version
    )

@app.get("/teams")
def all_teams() -> list[TeamResponse]:
    """
    Every team a game can be described with, one to an abbreviation.

    Only teams still playing are offered. The archive reaches back to franchises that folded and out
    to the overseas sides they toured against, and no prediction can name either.

    A tricode is how a request names a side, and the collected history holds franchises that share
    one. Only the first of them can ever be resolved back, so only that one is offered.
    """

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

@app.get("/teams/{abbreviation}/players")
def team_players(abbreviation: str) -> list[PlayerResponse]:
    """
    Who plays for a team, taken as everyone whose most recent game in the last year was for it.

    This is what fills the player list once a game has been chosen. There is no roster feed, so a
    player traded in the off season stays on their old team until they play for the new one.
    """

    player_ids = player_games.player_ids_on_team(team_id(abbreviation), season.today() - ROSTER_WINDOW)

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
    """
    What one model measured, narrowed to the figures it chose to publish and in that order.

    A figure the model asked for that the run did not score is left out rather than sent as a blank,
    which is what happens to a model whose answer shape gained a figure after it was last fitted.
    A model with nothing left to show reports no evaluation at all.
    """

    scored = metrics.read(specification.evaluation_file())
    if scored is None:
        return None

    shown = [
        MetricResponse(
            key=key,
            label=metrics.ALL_METRICS[key].label,
            description=metrics.ALL_METRICS[key].description,
            value=scored.metrics[key],
            floor=scored.floor.get(key),
            unit=metrics.ALL_METRICS[key].unit,
            higher_is_better=metrics.ALL_METRICS[key].higher_is_better
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
    """The family a caller named, or a 404 saying no such family is offered."""

    requested = next((candidate for candidate in ALL_FAMILIES if candidate.name == family), None)
    if requested is None:
        raise HTTPException(404, f"No model family is named {family}.")

    return requested

@app.get("/models/{family}/about")
def family_about_models(family: str) -> list[AboutModelResponse]:
    """
    The model cards for one family About page, with their explanatory copy and nothing measured.

    One request rather than one per model, because the page draws the whole family at once. The
    figures are not in it: they are read per model, when a reader opens one, so drawing the page
    costs no scored file it may never show.
    """

    requested = _family(family)

    return [
        AboutModelResponse(
            name=specification.name,
            title=specification.title,
            description=specification.description,
            published=requested.is_published(specification)
        )
        for specification in requested.specifications.values()
    ]

@app.get("/models/{family}/about/{model}/evaluation")
def model_evaluation(family: str, model: str) -> ModelEvaluationResponse | None:
    """
    What one model measured on its held-out games, asked for only when a reader opens that model.

    Null where it has never been scored, which is normal rather than an error: a model can be
    specified before it is fitted, and a run can be told to skip scoring. A caller shows the card
    without figures rather than hiding the model.
    """

    requested = _family(family)

    specification = requested.specifications.get(model)
    if specification is None:
        raise HTTPException(404, f"No model named {model} is in the {family} family.")

    return _model_evaluation(specification)
