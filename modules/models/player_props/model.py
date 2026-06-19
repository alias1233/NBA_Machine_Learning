import torch
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass

from . import data_processor

from src.training.model_architectures import feed_forward
from src.training.model_architectures.feed_forward import FeedForward


SAVE_MODEL_DIRECTORY_PATH = "trained_models/player_prop/"
INPUT_SCALER = 'input_scaler'

@dataclass
class ModelStructure():
    name: str
    target_stat: data_processor.TargetStat
    minimum_of_stat: int
    number_of_stat_classifications: int

PLAYER_PROPS_POINTS_MODEL = ModelStructure(
    "Points",
    data_processor.TargetStat.PLAYER_POINTS,
    0,
    60
    )

def load_model(model_structure: ModelStructure) -> tuple[torch.nn.Module, StandardScaler]:
    full_model_params = torch.load(SAVE_MODEL_DIRECTORY_PATH + model_structure.name + ".pth", weights_only=False)

    model = FeedForward(
        full_model_params[feed_forward.INPUT_DIM],
        full_model_params[feed_forward.OUTPUT_DIM],
        full_model_params[feed_forward.HIDDEN_LAYERS]
    )
    model.load_state_dict(
        full_model_params[feed_forward.MODEL_STATE]
    )

    return (model, full_model_params[INPUT_SCALER])

def save_model():
    pass