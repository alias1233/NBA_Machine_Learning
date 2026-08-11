"""
Predicting what happens in one game.

Everything specific to this family sits here: the request only it takes, and the endpoint that
answers it. A request names a game and nothing else, because neither side owns the answer. A point
differential still has a direction and is the home team's, which the family's inference module
decides.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nba_ml.api.schemas import GameRequest, PredictionResponse
from nba_ml.models import loading
from nba_ml.models.game_stats import inference, specifications

router = APIRouter(prefix="/predictions/game-stats", tags=["game_stats"])

class PredictionRequest(BaseModel):
    game: GameRequest

@router.post("/{model}")
def predict_game_stat(model: str, request: PredictionRequest) -> PredictionResponse:
    specification = specifications.ALL_MODEL_SPECIFICATIONS.get(model)
    if specification is None:
        raise HTTPException(404, f"No model is named {model}. See /models.")

    if not loading.can_load(specification):
        raise HTTPException(503, f"The {specification.name} model has no published file yet.")

    prediction = inference.predict(specification, request.game.to_game(), print_debug=False)

    return PredictionResponse(
        model=specification.name,
        output=specification.output,
        values=prediction.values,
        past_games=prediction.past_games
    )
