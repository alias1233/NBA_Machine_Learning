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

# Every prediction is capped here rather than in each family, because how many run at once is a
# property of the server rather than of the model. See nba_ml/api/limits.py.
for family_router in FAMILY_ROUTERS:
    app.include_router(family_router, dependencies=[Depends(limits.prediction_slot)])

# How far back a team's players are read from, for the players the roster snapshot says nothing
# about. Long enough that the answer survives an off season.
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

class RosterResponse(BaseModel):
    """
    One side of a game: who can be named for it, and how it is expected to differ from last time.

    The two lists are a RosterScenario already worked out, so a caller can offer them as the roster
    the reader would otherwise have had to enter by hand and still hand every name back to be
    changed. Both are empty where nothing collected says who will play. See nba_ml/expected_rosters.py.
    """

    team: TeamResponse
    players: list[PlayerResponse]
    """The team's projected roster, whether or not each of them played its last game."""

    without: list[PlayerResponse]
    """Who played the team's last game and is not expected to play this one."""

    returning: list[PlayerResponse]
    """Who is expected to play this one and did not play the last."""

class ModelResponse(BaseModel):
    name: str
    """What to pass as the model in a prediction request."""

    title: str
    """What the model is called where it is listed rather than run."""

    description: str
    """One sentence saying what it answers, for a reader who has not opened the family yet."""

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

    ideal: float | None
    """The value this figure should reach, where closeness defines the better result."""

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

class InfoModelResponse(BaseModel):
    """
    The model card a family Info page reads: the words it prints and the figures under them.

    The same words are on the catalogue, which is what a caller listing several families at once
    reads. This exists so the Info page is not handed the answer shapes it never looks at.
    """

    name: str
    """The stable model identifier."""

    title: str
    """The short reader-facing name."""

    description: str
    """The short reader-facing explanation."""

    published: bool
    """Whether a trained file exists."""

    evaluation: ModelEvaluationResponse | None
    """
    What the model measured on games it never saw, or null where it has never been scored.

    It travels with the card because the page it is drawn on is rendered on a server and read by
    search engines, and a figure fetched after the page has been sent reaches neither. Unscored is
    normal rather than an error: a model can be specified before it is fitted.
    """

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

    roster_snapshot: datetime | None
    """
    When the held roster and injury snapshot was collected, in UTC.

    Null while none has been, which is what makes every side of every game open on the lineup it last
    played. A stale one reads as a player who has since been ruled out still taking the floor.
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
        feature_build=None if build is None else build.version,
        roster_snapshot=rosters.collected_at()
    )

@app.get("/showcase")
def todays_showcase() -> dict | None:
    """
    The day's sample predictions, built by a job rather than by this request.

    Read straight off the published file and passed on as it stands. Nothing is predicted here: this
    endpoint exists precisely so that a visitor arriving at the home page starts no forward pass, and
    it is deliberately outside the prediction cap because it costs one file read.

    Null where no set has been published, which is what a machine that has never run the job looks
    like. A caller draws its page without samples rather than treating it as a failure. See
    nba_ml/showcase.py.
    """

    return showcase.read()

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

def _named(player_ids: Collection[int]) -> list[PlayerResponse]:
    """The named players among the given ids, alphabetically, which is how a list of them is read."""

    return [
        PlayerResponse(id=player.id, name=player.name)
        for player in sorted(players.get_players(player_ids), key=lambda player: player.name)
    ]

def _roster(team: Team, game: Game) -> RosterResponse:
    """
    One side of a game: the roster it is projected to field, and how it is expected to line up.

    Everyone the collected snapshot puts on the team, plus everyone whose most recent game in the
    last year was for it and whom the snapshot does not place elsewhere. Neither half is the roster
    on its own. The snapshot leaves out anybody the provider has not listed, and the played games go
    on offering a player who has since been traded away.

    A player the snapshot says nothing about is left where their last game put them, which is how a
    provider that has simply not listed somebody is told apart from one that has dropped them. With
    no snapshot held that is every player, so this is the played games alone, exactly as it was
    before any roster was collected.

    A projected player the archive has never named is not offered, because nothing about their box
    score line could be predicted anyway.
    """

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
    """
    Both sides of a scheduled game, away first, which is the order a matchup is written in.

    This is what fills the roster controls once a game has been chosen. Each side arrives with the
    lineup change the collected snapshot expects of it, so a caller can offer that as the reader's
    starting point rather than an empty form. See nba_ml/expected_rosters.py.
    """

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
    """The family a caller named, or a 404 saying no such family is offered."""

    requested = next((candidate for candidate in ALL_FAMILIES if candidate.name == family), None)
    if requested is None:
        raise HTTPException(404, f"No model family is named {family}.")

    return requested

@app.get("/models/{family}/info")
def family_info_models(family: str) -> list[InfoModelResponse]:
    """
    The model cards for one family Info page, with their explanatory copy and their figures.

    One request rather than one per model, because the page draws the whole family at once and is
    rendered before it is sent. Each card carries its own scored file, read here, so the page holds
    every figure it prints. A family is a dozen or so small JSON files, which is cheaper than the
    round trips a browser would otherwise make one at a time.
    """

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
