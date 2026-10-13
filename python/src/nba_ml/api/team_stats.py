"""Prediction endpoint for the team stats models."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nba_ml.api.schemas import GameRequest, GameRostersRequest, PredictionResponse, team_id
from nba_ml.models import loading
from nba_ml.models.team_stats import inference, specifications

router = APIRouter(prefix="/predictions/team-stats", tags=["team_stats"])

class PredictionRequest(BaseModel):
    team: str
    """The team to predict for, as an abbreviation (e.g. LAL) or full team name."""

    game: GameRequest
    rosters: GameRostersRequest = Field(default_factory=GameRostersRequest)
    """Players each team is missing or getting back for this game."""

@router.post("/{model}")
def predict_team_stat(model: str, request: PredictionRequest) -> PredictionResponse:
    specification = specifications.ALL_MODEL_SPECIFICATIONS.get(model)
    if specification is None:
        raise HTTPException(404, f"No model is named {model}. See /models.")

    game = request.game.to_game()
    target_team_id = team_id(request.team)

    if target_team_id not in (game.home_team_id, game.away_team_id):
        raise HTTPException(400, f"{request.team} is not playing in this game.")

    if not loading.can_load(specification):
        raise HTTPException(503, f"The {specification.name} model has no published file yet.")

    prediction = inference.predict(
        specification,
        target_team_id,
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
