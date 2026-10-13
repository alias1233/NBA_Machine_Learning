"""Prediction endpoint for the game stats models."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nba_ml.api.schemas import GameRequest, GameRostersRequest, PredictionResponse
from nba_ml.models import loading
from nba_ml.models.game_stats import inference, specifications

router = APIRouter(prefix="/predictions/game-stats", tags=["game_stats"])

class PredictionRequest(BaseModel):
    game: GameRequest
    rosters: GameRostersRequest = Field(default_factory=GameRostersRequest)
    """Players each team is missing or getting back for this game."""

@router.post("/{model}")
def predict_game_stat(model: str, request: PredictionRequest) -> PredictionResponse:
    specification = specifications.ALL_MODEL_SPECIFICATIONS.get(model)
    if specification is None:
        raise HTTPException(404, f"No model is named {model}. See /models.")

    if not loading.can_load(specification):
        raise HTTPException(503, f"The {specification.name} model has no published file yet.")

    game = request.game.to_game()
    prediction = inference.predict(
        specification,
        game,
        request.rosters.to_scenarios(game),
        print_debug=False
    )

    return PredictionResponse(
        model=specification.name,
        output=specification.output,
        values=prediction.values,
        past_games=prediction.past_games
    )
