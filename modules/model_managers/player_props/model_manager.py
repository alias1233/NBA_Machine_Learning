from dataclasses import dataclass, field
import numpy as np
import torch, torch.nn as nn
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import StandardScaler
import math

from . import data_processor
from .. import directories
from src.data_preprocessing import training_data_processing
from src.data_preparation import nba_data_helpers
from src.training import trainer, helpers, evaluation
from src.training.model_architectures.feed_forward import FeedForward, LayerParameters

MODEL_CATEGORY = "player_prop"
INPUT_SCALER = 'input_scaler'

# Models
@dataclass
class ModelSpecification():
    name: str
    target_stats: list[data_processor.TargetStat]
    minimum_of_stat: int
    number_of_stat_classifications: int

    save_model_file_path: str = field(init=False)

    def __post_init__(self):
        self.save_model_file_path = directories.get_model_save_path(self.name, MODEL_CATEGORY)

PLAYER_PROPS_POINTS_MODEL = ModelSpecification(
    "points",
    [data_processor.TargetStat.POINTS],
    0,
    60
    )

PLAYER_PROPS_REBOUNDS_MODEL = ModelSpecification(
    "rebounds",
    [data_processor.TargetStat.REBOUNDS],
    0,
    25
    )

PLAYER_PROPS_ASSISTS_MODEL = ModelSpecification(
    "assists",
    [data_processor.TargetStat.ASSISTS],
    0,
    20
    )

PLAYER_PROPS_POINTS_REBOUNDS_ASSISTS_MODEL = ModelSpecification(
    "points_rebounds_assists",
    [data_processor.TargetStat.POINTS,
    data_processor.TargetStat.REBOUNDS,
    data_processor.TargetStat.ASSISTS],
    0,
    (PLAYER_PROPS_POINTS_MODEL.number_of_stat_classifications + 
    PLAYER_PROPS_REBOUNDS_MODEL.number_of_stat_classifications + 
    PLAYER_PROPS_ASSISTS_MODEL.number_of_stat_classifications)
)

# Training
SAVE_PROCESSED_TRAINING_DATA = True
LOAD_SAVED_PROCESSED_TRAINING_DATA = False

RANDOM_SEED = 12156666

CHUNK_STEP_SIZE = 1
VALIDATION_START_DATE = datetime(2026, 1, 1)
TEST_START_DATE = datetime(2026, 3, 1)

HIDDEN_LAYERS_PARAMETERS = [
    LayerParameters(512, nn.ReLU(), True, 0.45),
    LayerParameters(256, nn.ReLU(), True, 0.35),
    LayerParameters(128, nn.ReLU(), True, 0.3),
]

HIDDEN_LAYERS_PARAMETERS = [
    LayerParameters(512, nn.LeakyReLU(0.1), True, 0.45),
    LayerParameters(256, nn.LeakyReLU(0.1), True, 0.35),
    LayerParameters(256, nn.LeakyReLU(0.1), True, 0.35),
    LayerParameters(128, nn.LeakyReLU(0.1), True, 0.25),
]

LEARNING_RATE = 0.00001
EPOCHS = 25
LOSS_FUNCTION: trainer.LossFunction = torch.nn.CrossEntropyLoss()
EVALUATION_INTERVAL = 1
BATCH_SIZE = 128
PATIENCE = -1
MIN_DELTA = 0.001
DEVICE = helpers.get_best_device()
LOG_LOSS_INTERVAL = 1

# TESTING OVERPARAMETERIZATION #
# HIDDEN_LAYERS_PARAMETERS = [
#     LayerParameters(1024, nn.ReLU(), True, 0.2),
#     LayerParameters(512, nn.ReLU(), True, 0.15),
#     LayerParameters(512, nn.ReLU(), True, 0.15),
#     LayerParameters(256, nn.ReLU(), True, 0.1),
# ]

# LEARNING_RATE = 0.001
# EPOCHS = 50
# LOSS_FUNCTION: trainer.LossFunction = torch.nn.CrossEntropyLoss()
# EVALUATION_INTERVAL = 1
# BATCH_SIZE = 512
# PATIENCE = -1
# MIN_DELTA = 0.001
# DEVICE = helpers.get_best_device()
# LOG_LOSS_INTERVAL = 1
# END TEST

INPUT_SCALER = 'input_scaler'

# Move somewhere else
def get_preprocessed_training_data(
        model_specs: ModelSpecification,
        print_debug: bool = False,
        print_all_debug: bool = False
        ) -> tuple:
    
    if LOAD_SAVED_PROCESSED_TRAINING_DATA:
        if print_debug:
            print("Loading in preprocessed data...")

        return helpers.load_data_from_file(directories.get_model_save_training_data_path(model_specs.name, MODEL_CATEGORY))
    
    labeled_datasets = data_processor.get_all_player_props_input_output_labeled_data(
        model_specs.target_stats,
        VALIDATION_START_DATE,
        TEST_START_DATE,
        CHUNK_STEP_SIZE,
        print_debug
    )

    helpers.print_labeled_dataset(labeled_datasets, print_all_debug, print_debug)

    datasets = training_data_processing.process_labeled_data_for_classification_training(
        *labeled_datasets, 
        flatten=True,
        standardize_input=True,
        min_output_value=model_specs.minimum_of_stat,
        num_classifications=model_specs.number_of_stat_classifications
        )
    
    helpers.print_datasets(datasets, 1, print_all_debug, print_debug)

    if SAVE_PROCESSED_TRAINING_DATA and not LOAD_SAVED_PROCESSED_TRAINING_DATA:
        if print_debug:
            print("Saving preprocessed data...")

        helpers.save_data_to_file(directories.get_model_save_training_data_path(model_specs.name, MODEL_CATEGORY), datasets)

    return datasets
    
def train(
        model_specs: ModelSpecification,
        output_evaluations: bool = True,
        print_debug: bool = True, 
        print_all_debug: bool = False,
        ):
    
    if print_all_debug:
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    (input_train, output_train, 
     input_val, output_val, 
     input_test, output_test, 
     input_scaler
     ) = get_preprocessed_training_data(
         model_specs,
         print_debug, 
         print_all_debug
         )
    
    # TESTING WITH LARGER VALIDATION DATASET
    input_val = torch.concat((input_val, input_test))
    output_val = torch.concat((output_val, output_test))
    input_test = input_val
    output_test = output_val
    # END TEST
 
    if print_debug:
        print(f"Input feature dimensions: {str(input_train.shape)}")
        print(f"Output feature dimensions: {str(output_train.shape)}")
        print(f"Device: {DEVICE}")

    in_features = input_train.shape[1]
    out_features = model_specs.number_of_stat_classifications

    # Creating model and training
    model = FeedForward(
        in_features,
        out_features,
        HIDDEN_LAYERS_PARAMETERS,
        True
    )

    optimizer = torch.optim.AdamW(
        model.parameters(), 
        lr=LEARNING_RATE
    )

    training_progress = trainer.train(
        model,
        input_train,
        output_train,
        input_val,
        output_val,
        optimizer,
        loss_function=LOSS_FUNCTION,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        patience=PATIENCE,
        min_delta=MIN_DELTA,
        device=DEVICE,
        evaluation_interval=EVALUATION_INTERVAL,
        log_loss_interval=LOG_LOSS_INTERVAL
    )

    # Saving model data
    model_params = model.get_save_parameters_dict()
    scaler_params = {
        INPUT_SCALER : input_scaler
    }

    helpers.save_dictionary_data_to_file(model_specs.save_model_file_path, [model_params, scaler_params])

    if not output_evaluations:
        return
    
    if training_progress is not None:
        trainer.graph_loss_progress(
            training_progress, 
            directories.get_model_save_graphs_directory_path(model_specs.name, MODEL_CATEGORY)
            )

    # Final evaluation on validation dataset
    parameters_dict = helpers.load_data_from_file(model_specs.save_model_file_path)
    model = FeedForward.load_from_saved_parameters_dict(
        parameters_dict
    )

    model.eval()
    with torch.no_grad():
        predictions: torch.Tensor = model(input_test).cpu()

    print(f"Evaluation Chunks: {len(input_test)}" )

    loss = LOSS_FUNCTION(predictions, output_test)
    print(f"Test loss: {loss}")

    predictions_numpy = predictions.numpy()
    actuals_numpy = output_test.numpy()

    evaluation.output_test_evaluation_classification(
        predictions_numpy,
        actuals_numpy,
        label=model_specs.name,
        ordinal=True,
        output_size=20,
        save_graph_directory_path=directories.get_model_save_graphs_directory_path(model_specs.name, MODEL_CATEGORY)
    )

# Predicting
def predict(
    model_specs: ModelSpecification,
    target_player_id: int,
    target_player_team_id: int,
    target_player_opponent_team_id: int,
    target_game_date: datetime,
    target_game_season_type: nba_data_helpers.SeasonTypes,
    target_game_at_home: bool,
    target_player_removed_core_teammate_player_ids: set[int],
    target_player_added_core_teammate_player_ids: set[int],
    ) -> list[float]:

    input_labeled = data_processor.get_player_prop_inference_labeled_input_data(
        model_specs.target_stats,
        target_player_id,
        target_player_team_id,
        target_player_opponent_team_id,
        target_game_date,
        target_game_season_type,
        target_game_at_home,
        target_player_removed_core_teammate_player_ids,
        target_player_added_core_teammate_player_ids,
        print_debug=True
    )

    input_processed = training_data_processing.process_labeled_input(
        input_labeled,
        True
    )

    parameters_dict = helpers.load_data_from_file(model_specs.save_model_file_path)
    model = FeedForward.load_from_saved_parameters_dict(
        parameters_dict
    )
    input_scaler: StandardScaler = parameters_dict[INPUT_SCALER]

    input_scaled = input_scaler.transform(input_processed)
    input: torch.Tensor = training_data_processing.to_tensor(input_scaled)

    model.eval()
    with torch.no_grad():
        predictions: torch.Tensor = model(input).cpu()

    predicted_probabilities = torch.softmax(predictions, 1)

    return predicted_probabilities.tolist()[0]

def calculate_odds_over_line(
    predicted_probabilities: list[float],
    over_under_line: float,
    minimum_value: int = 0
    ) -> float:
    """
    Calculates the probability given the probability distribution of a value to be higher than the
    given over_under_line.

    Args:
        predicted_probabilities is a list of floats where the value at each index represents the predicted probabilty of
        the value represented by that index of occuring. Each value is assumed to be ordered and in increments of exactly 1.

        over_under_line is a threshold set that a given value has a chance of exceeding.

        minimum_value is the value that the index at 0 of the predicted_probability represents.
    """

    above_line_threshold = math.ceil(over_under_line) - minimum_value

    probability_exceeds_over_under: float = 0.0
    for value in range(above_line_threshold, len(predicted_probabilities)):
        probability_exceeds_over_under += predicted_probabilities[value]

    return probability_exceeds_over_under