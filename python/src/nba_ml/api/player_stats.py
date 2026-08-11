"""
Predicting one player's statistic in one game.

Everything specific to this family sits here: the request only it takes, and the endpoint that
answers it. Another family is another module of the same shape, mounted alongside this one.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nba_ml.api.schemas import GameRequest, PredictionResponse, team_id
from nba_ml.models import loading
from nba_ml.models.player_stats import inference, specifications
from nba_ml.stores import players

router = APIRouter(prefix="/predictions/player-stats", tags=["player_stats"])

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

@router.post("/{model}")
def predict_player_stat(model: str, request: PredictionRequest) -> PredictionResponse:
    specification = specifications.ALL_MODEL_SPECIFICATIONS.get(model)
    if specification is None:
        raise HTTPException(404, f"No model is named {model}. See /models.")

    if players.get_player(request.player_id) is None:
        raise HTTPException(404, f"No stored player has the id {request.player_id}.")

    if not loading.can_load(specification):
        raise HTTPException(503, f"The {specification.name} model has no published file yet.")

    prediction = inference.predict(
        specification,
        request.player_id,
        request.game.to_game(),
        set(request.scenario.without),
        set(request.scenario.returning),
        target_player_team_id=None if request.player_team is None else team_id(request.player_team),
        print_debug=False
    )

    return PredictionResponse(
        model=specification.name,
        output=specification.output,
        values=prediction.values,
        past_games=prediction.past_games
    )
