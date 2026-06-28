from dataclasses import dataclass

from . import data_processor


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