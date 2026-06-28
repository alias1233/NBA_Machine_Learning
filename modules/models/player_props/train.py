from datetime import datetime
import numpy as np
import torch, torch.nn as nn
import pandas as pd

from . import data_processor
from modules.models import directories
from src.data_preprocessing import training_data_processing
from src.training import trainer, helpers, evaluation
from src.training.model_architectures.feed_forward import FeedForward, LayerParameters

MODEL_NAME = "player_prop_points"

SAVE_MODEL_FILE_PATH = directories.SAVE_MODELS_DIRECTORY_PATH + MODEL_NAME + '/model.pth'

MODEL_SAVE_GRAPHS_DIRECTORY_PATH = directories.SAVE_GRAPHS_DIRECTORY_PATH + MODEL_NAME

SAVE_PROCESSED_TRAINING_DATA_PATH = directories.SAVE_PROCESSED_TRAINING_DATA_PATH + MODEL_NAME + '/training_data.pth'
SAVE_PROCESSED_TRAINING_DATA = True
LOAD_SAVED_PROCESSED_TRAINING_DATA = True

RANDOM_SEED = 12156666

TARGET_STAT = data_processor.TargetStat.PLAYER_POINTS
MINIMUM_OF_STAT = 0
NUM_STAT_CLASSIFICATIONS = 60

CHUNK_STEP_SIZE = 1
VALIDATION_START_DATE = datetime(2026, 1, 1)
TEST_START_DATE = datetime(2026, 3, 1)

HIDDEN_LAYERS_PARAMETERS = [
    LayerParameters(512, nn.ReLU(), True, 0.45),
    LayerParameters(256, nn.ReLU(), True, 0.35),
    LayerParameters(128, nn.ReLU(), True, 0.3),
]

HIDDEN_LAYERS_PARAMETERS = [
    LayerParameters(512, nn.LeakyReLU(), True, 0.45),
    LayerParameters(256, nn.LeakyReLU(), True, 0.35),
    LayerParameters(256, nn.LeakyReLU(), True, 0.3),
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

INPUT_SCALER = 'input_scaler'

# Move somewhere else
def get_preprocessed_training_data(
        print_debug: bool = False,
        print_all_debug: bool = False
        ) -> tuple:
    
    if LOAD_SAVED_PROCESSED_TRAINING_DATA:
        if print_debug:
            print("Loading in preprocessed data...")

        return helpers.load_data_from_file(SAVE_PROCESSED_TRAINING_DATA_PATH)
    
    labeled_datasets = data_processor.get_all_player_props_input_output_labeled_data(
        TARGET_STAT,
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
        min_output_value=MINIMUM_OF_STAT,
        num_classifications=NUM_STAT_CLASSIFICATIONS
        )
    
    helpers.print_datasets(datasets, 1, print_all_debug, print_debug)

    if SAVE_PROCESSED_TRAINING_DATA and not LOAD_SAVED_PROCESSED_TRAINING_DATA:
        if print_debug:
            print("Saving preprocessed data...")

        helpers.save_data_to_file(SAVE_PROCESSED_TRAINING_DATA_PATH, datasets)

    return datasets
    
def train(
        print_debug: bool = True, 
        print_all_debug: bool = False
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
         print_debug, 
         print_all_debug
         )
 
    if print_debug:
        print(f"Input feature dimensions: {str(input_train.shape)}")
        print(f"Output feature dimensions: {str(output_train.shape)}")
        print(f"Device: {DEVICE}")

    in_features = input_train.shape[1]
    out_features = NUM_STAT_CLASSIFICATIONS

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

    trainer.train(
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

    helpers.save_dictionary_data_to_file(SAVE_MODEL_FILE_PATH, [model_params, scaler_params])

    # Final evaluation on validation dataset
    parameters_dict = helpers.load_data_from_file(SAVE_MODEL_FILE_PATH)
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
        label=TARGET_STAT.value,
        ordinal=True,
        output_size=20,
        save_graph_directory_path=MODEL_SAVE_GRAPHS_DIRECTORY_PATH
    )